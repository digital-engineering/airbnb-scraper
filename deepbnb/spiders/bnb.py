# -*- coding: utf-8 -*-
import json
import re
import scrapy

from deepbnb.items import DeepbnbItem
from urllib.parse import urlencode, urlunparse


class BnbSpider(scrapy.Spider):
    name = 'bnb'
    allowed_domains = ['airbnb.com']
    default_currency = 'USD'
    default_max_price = 3000
    default_price_increment = 100
    price_range = (0, default_max_price, default_price_increment)
    page_limit = 20

    def __init__(
            self,
            query,
            checkin=None,
            checkout=None,
            currency=default_currency,
            max_price=None,
            min_price=None,
            **kwargs
    ):
        """Class constructor."""
        super().__init__(**kwargs)
        self._api_key = None
        self._checkin = checkin
        self._checkout = checkout
        self._currency = currency
        self._data_cache = {}
        self._geography = {}
        self._neighborhoods = {}
        self._place = query
        self._search_params = {}

        self._max_price = max_price
        self._min_price = min_price
        if self._min_price and self._max_price:
            self._max_price = int(self._max_price)
            self._min_price = int(self._min_price)
            self.price_range = (self._min_price, self._max_price, self.default_price_increment)

        if self._min_price and not self._max_price:
            self._min_price = int(self._min_price)
            self.price_range = (self._min_price, self.default_max_price, self.default_price_increment)

        if not self._min_price and self._max_price:
            self._max_price = int(self._max_price)
            self.price_range = (0, self._max_price, self.default_price_increment)

    @staticmethod
    def iterate_neighborhoods(neighborhoods):
        for neighborhood in neighborhoods:
            yield {'neighborhood_ids[]': neighborhood['id']}

    @staticmethod
    def iterate_prices(price_range):
        price_range_min, price_range_max, price_inc = price_range
        price_range_min = max(price_range_min, 0)
        price_range_max = max(price_range_max, price_range_min + price_inc)

        for price_min in range(price_range_min, price_range_max, price_inc):
            price_max = price_min + price_inc
            params = {}
            if price_min > price_range_min:
                params['price_min'] = price_min
            if price_max < price_range_max:
                params['price_max'] = price_max

            yield params

    def parse(self, response):
        """Default parse method."""
        data = self.read_data(response)
        tab = data['explore_tabs'][0]

        # Handle pagination
        pagination = tab['pagination_metadata']
        if pagination['has_next_page']:
            items_offset = pagination['items_offset']
            next_section = self._search_params.copy()
            next_section.update({'items_offset': items_offset})
            yield self._api_request(params=next_section, response=response)

        # handle listings
        params = {
            '_format': 'for_rooms_show',
            'key':     self._api_key,
        }

        if self._checkin:
            params['checkin'] = self._checkin
            params['checkout'] = self._checkout

        if self._max_price:
            params['price_max'] = self._max_price

        if self._min_price:
            params['price_min'] = self._min_price

        listings = self._get_listings_from_sections(tab['sections'])
        for listing in listings:  # request each property page
            yield self._listing_api_request(listing, params)

    def parse_landing_page(self, response):
        """Parse search response and generate URLs for all searches, then perform them."""
        data = self.read_data(response)
        self._search_params = self._get_search_params(data)
        self._neighborhoods = self._get_neighborhoods(data)

        tab = data['explore_tabs'][0]
        metadata = tab['home_tab_metadata']
        self._geography = metadata['geography']

        self.logger.info(f"Geography:\n{self._geography}")
        self.logger.info(f"Neighborhoods:\n{self._neighborhoods}")

        if self._neighborhoods:  # iterate by neighborhood
            for neighborhood in self.iterate_neighborhoods(self._neighborhoods.values()):
                for price in self.iterate_prices(self.price_range):
                    params = self._search_params.copy()
                    params.update(neighborhood)
                    params.update(price)
                    yield self._api_request(params=params, response=response, callback=self.parse)

        else:  # iterate by search pagination
            params = self._search_params.copy()
            yield self._api_request(params=params, response=response, callback=self.parse)

    def read_data(self, response):
        """Read response data as json"""
        self.logger.debug(f"Parsing {response.url}")
        data = json.loads(response.body)
        return data

    def start_requests(self):
        """Application entry point. Generate the first search request."""
        self.logger.info(f"starting survey for: {self._place}")
        params = {}
        if self._checkin:
            params['checkin'] = self._checkin
            params['checkout'] = self._checkout

        if self._max_price:
            params['price_max'] = self._max_price

        yield self._api_request(params, callback=self.parse_landing_page)

    def _api_request(self, params=None, response=None, callback=None):
        """Perform API request."""
        if response:
            request = response.follow
        else:
            request = scrapy.Request

        callback = callback or self.parse

        return request(self._get_search_api_url(params), callback)

    @staticmethod
    def _build_airbnb_url(path, query=None):
        if query is not None:
            query = urlencode(query)

        parts = ['https', 'www.airbnb.com', path, None, query, None]
        return urlunparse(parts)

    def _get_listings_from_sections(self, sections):
        """Get listings from sections, also collect some data and save it for later."""
        listings = []
        for s in sections:
            if 'listings' not in s:
                continue

            for listing in s['listings']:
                listing_id = listing['listing']['id']
                pricing = listing['pricing_quote']
                self._data_cache[listing_id] = {}
                self._data_cache[listing_id]['monthly_price_factor'] = pricing['monthly_price_factor']
                self._data_cache[listing_id]['weekly_price_factor'] = pricing['weekly_price_factor']

                if self._checkin:  # use total price if dates given, price rate otherwise
                    self._data_cache[listing_id]['price_rate'] = pricing['rate_with_service_fee']['amount']
                    self._data_cache[listing_id]['price_rate_type'] = pricing['rate_type']
                    self._data_cache[listing_id]['total_price'] = pricing['price']['total']['amount']
                else:
                    self._data_cache[listing_id]['price_rate'] = pricing['rate_with_service_fee']['amount']
                    self._data_cache[listing_id]['price_rate_type'] = pricing['rate_type']
                    self._data_cache[listing_id]['total_price'] = None

                listings.append(listing)

        return listings

    @staticmethod
    def _get_neighborhoods(data):
        """Get all neighborhoods in an area if they exist."""
        neighborhoods = {}
        meta = data['explore_tabs'][0]['home_tab_metadata']
        if meta['listings_count'] < 300:
            return neighborhoods

        for section in meta['filters']['sections']:
            if section['filter_section_id'] != 'neighborhoods':
                continue
            for item in section['items']:
                key = item['title']
                neighborhoods[key] = item
                for param in item['params']:
                    if param['key'] == 'neighborhood_ids':
                        neighborhoods[key]['id'] = param['value']
                        break

        return neighborhoods

    def _get_search_api_url(self, params=None):
        _api_path = '/api/v2/explore_tabs'
        if self._api_key is None:
            self._api_key = self.settings.get("AIRBNB_API_KEY")

        query = {
            '_format':                       'for_explore_search_web',
            'auto_ib':                       'true',  # was false?
            'currency':                      self._currency,
            'current_tab_id':                'home_tab',
            'experiences_per_grid':          '20',
            # 'federated_search_session_id': '',
            'fetch_filters':                 'true',
            'guidebooks_per_grid':           '20',
            'has_zero_guest_treatment':      'false',
            'hide_dates_and_guests_filters': 'false',
            'is_guided_search':              'true',
            'is_new_cards_experiment':       'true',
            'is_standard_search':            'true',
            # 'items_offset': '0',
            'items_per_grid':                '50',
            'key':                           self._api_key,
            # 'last_search_session_id': '',
            'locale':                        'en',
            'metadata_only':                 'false',
            # 'neighborhood_ids[]': ,
            # 'place_id': '',
            # 'price_max': None,
            # 'price_min': 10,
            'query':                         self._place,
            'query_understanding_enabled':   'true',
            'refinement_paths[]':            '/homes',
            'room_types[]':                  'Entire home/apt',
            'satori_version':                '1.2.0',
            # 'section_offset': '0',
            'screen_height':                 635,
            'screen_size':                   'large',
            'screen_width':                  2040,
            'show_groupings':                'true',
            'supports_for_you_v3':           'true',
            'timezone_offset':               '-480',
            'version':                       '1.6.5'
        }

        if params:
            query.update(params)

        if self.settings.get('PROPERTY_AMENITIES'):
            amenities = self.settings.get('PROPERTY_AMENITIES').values()
            query = list(query.items())  # convert dict to list of tuples because we need multiple identical keys
            for a in amenities:
                query.append(('amenities[]', a))

        return self._build_airbnb_url(_api_path, query)

    def _get_search_params(self, data):
        """Consolidate search parameters and return result."""
        tab = data['explore_tabs'][0]
        pagination = tab['pagination_metadata']
        metadata = tab['home_tab_metadata']
        geography = metadata['geography']
        location = metadata['location']
        params = {
            'federated_search_session_id':
                data['metadata']['federated_search_session_id'],
            'place_id':
                geography['place_id'],
            'query':
                location['canonical_location']
        }

        if pagination['has_next_page']:
            params['last_search_session_id'] = pagination['search_session_id']

        if self._checkin:
            params['checkin'] = self._checkin
            params['checkout'] = self._checkout

        if self._max_price:
            params['price_max'] = self._max_price

        return params

    def _listing_api_request(self, listing, params):
        """Generate scrapy.Request for single listing."""
        api_path = '/api/v2/pdp_listing_details'
        url = self._build_airbnb_url('{}/{}'.format(api_path, listing['listing']['id']), params)
        return scrapy.Request(url, callback=self._parse_listing_contents)

    @staticmethod
    def _parse_bedrooms(listing) -> int:
        """Get bedrooms from listing, return integer."""
        bedrooms = 0
        if 'bedrooms' in listing:
            bedrooms = listing['bedrooms']
        elif 'bedroom_label' in listing:
            if listing['bedroom_label'] == 'Studio':
                bedrooms = 0
            else:
                result = re.search(r'\d+', listing['bedroom_label'])
                if result:
                    bedrooms = int(result[0])
                else:
                    raise RuntimeError(f'Unhandled bedroom_label: {listing["bedroom_label"]}')

        return bedrooms

    def _parse_listing_contents(self, response):
        """Obtain data from an individual listing page."""
        data = self.read_data(response)
        listing = data['pdp_listing_detail']
        listing_id = listing['id']  # photos?

        item = DeepbnbItem(
            id=listing_id,
            access=listing['sectioned_description']['access'],
            additional_house_rules=listing['additional_house_rules'],
            allows_events=listing['guest_controls']['allows_events'],
            amenities={la['id']: la['name'] for la in listing['listing_amenities'] if la['is_present']},
            bathrooms=listing.get('bathrooms', re.search(r'\d+(\.\d+)?', listing['bathroom_label'])[0]),
            bedrooms=self._parse_bedrooms(listing),
            beds=listing.get('beds', re.search(r'\d+', listing['bed_label'])[0]),
            business_travel_ready=listing['is_business_travel_ready'],
            city=self._geography['city'],
            country=self._geography['country'],
            country_code=self._geography['country_code'],
            description=listing['sectioned_description']['description'],
            host_id=listing['primary_host']['id'],
            house_rules=listing['sectioned_description']['house_rules'],
            is_hotel=listing['is_hotel'],
            latitude=listing['lat'],
            longitude=listing['lng'],
            max_nights=listing.get('max_nights'),
            min_nights=listing['min_nights'],
            monthly_price_factor=self._data_cache[listing_id]['monthly_price_factor'],
            name=listing.get('name', listing_id),
            neighborhood_overview=listing['sectioned_description']['neighborhood_overview'],
            notes=listing['sectioned_description']['notes'],
            person_capacity=listing['person_capacity'],
            photo_count=len(listing['photos']),
            place_id=self._geography['place_id'],
            price_rate=self._data_cache[listing_id]['price_rate'],
            price_rate_type=self._data_cache[listing_id]['price_rate_type'],
            province=self._geography.get('province'),
            rating_accuracy=listing['p3_event_data_logging']['accuracy_rating'],
            rating_checkin=listing['p3_event_data_logging']['checkin_rating'],
            rating_cleanliness=listing['p3_event_data_logging']['cleanliness_rating'],
            rating_communication=listing['p3_event_data_logging']['communication_rating'],
            rating_location=listing['p3_event_data_logging']['location_rating'],
            rating_value=listing['p3_event_data_logging']['value_rating'],
            review_count=listing['review_details_interface']['review_count'],
            review_score=listing['review_details_interface']['review_score'],
            room_and_property_type=listing['room_and_property_type'],
            room_type=listing['room_type_category'],
            satisfaction_guest=listing['p3_event_data_logging']['guest_satisfaction_overall'],
            star_rating=listing['star_rating'],
            state=self._geography['state'],
            state_short=self._geography['state_short'],
            summary=listing['sectioned_description']['summary'],
            total_price=self._data_cache[listing_id]['total_price'],
            transit=listing['sectioned_description']['transit'],
            url="https://www.airbnb.com/rooms/{}".format(listing['id']),
            weekly_price_factor=self._data_cache[listing_id]['weekly_price_factor']
        )

        if 'interaction' in listing['sectioned_description'] and listing['sectioned_description']['interaction']:
            item['interaction'] = listing['sectioned_description']['interaction']

        return item
