# -*- coding: utf-8 -*-
import json
import scrapy

from deepbnb.items import DeepbnbItem
from urllib.parse import urlencode, urlunparse


class BnbSpider(scrapy.Spider):
    name = 'bnb'
    allowed_domains = ['airbnb.com']
    default_currency = 'USD'
    price_range = (0, 2000, 10)
    page_limit = 20

    def __init__(self, query, currency=default_currency, checkin=None, checkout=None, **kwargs):
        super().__init__(**kwargs)
        self._api_path = "/api/v2/explore_tabs"
        self._api_key = None
        self._checkin = checkin
        self._checkout = checkout
        self._currency = currency
        self._data_cache = {}
        self._geography = {}
        self._neighborhoods = {}
        self._place = query
        self._search_params = {}

    @staticmethod
    def iterate_neighborhoods(neighborhoods):
        for neighborhood in neighborhoods:
            yield {'neighborhood_ids[]': neighborhood['id']}

    @staticmethod
    def iterate_prices(price_range):
        # Iterate prices
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
        data = self.read_data(response)
        tab = data['explore_tabs'][0]

        # Handle pagination
        pagination = tab['pagination_metadata']
        if pagination['has_next_page']:
            items_offset = pagination['items_offset']
            next_section = self._search_params.copy()
            next_section.update({'items_offset': items_offset})
            yield self._api_request(params=next_section, response=response)

        params = {}
        if self._checkin:
            params['checkin'] = self._checkin
            params['checkout'] = self._checkout

        listings = self._get_listings_from_sections(tab['sections'])
        for listing in listings:  # request each property page
            url = self._build_airbnb_url('/rooms/{}'.format(listing['listing']['id']), params)
            yield scrapy.Request(url, callback=self._parse_listing_contents)

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

        # Iterate area
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
        self.logger.debug(f"Parsing {response.url}")
        data = json.loads(response.body)
        return data

    def start_requests(self):
        """Generate the first search request."""
        self.logger.info(f"starting survey for: {self._place}")
        params = {}
        if self._checkin:
            params['checkin'] = self._checkin
            params['checkout'] = self._checkout

        yield self._api_request(params, callback=self.parse_landing_page)

    def _api_request(self, params=None, response=None, callback=None):
        if response:
            request = response.follow
        else:
            request = scrapy.Request

        callback = callback or self.parse

        return request(self._api_url(params), callback)

    def _api_url(self, params=None):
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

        return self._build_airbnb_url(self._api_path, query)

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
                    self._data_cache[listing_id]['price_rate'] = None
                    self._data_cache[listing_id]['price_rate_type'] = None
                    self._data_cache[listing_id]['total_price'] = pricing['price']['total']['amount']
                else:
                    self._data_cache[listing_id]['price_rate'] = pricing['rate_with_service_fee']['amount']
                    self._data_cache[listing_id]['price_rate_type'] = pricing['rate_type']
                    self._data_cache[listing_id]['total_price'] = None

                listings.append(listing)

        return listings

    @staticmethod
    def _get_neighborhoods(data):
        meta = data['explore_tabs'][0]['home_tab_metadata']
        facets = meta['facets'].get('neighborhood_facet', [])

        neighborhoods = {}
        for item in facets:
            neighborhoods[item['key']] = item

        for section in meta['filters']['sections']:
            if section['filter_section_id'] == 'neighborhoods':
                for item in section['items']:
                    key = item['title']
                    for param in item['params']:
                        if param['key'] == 'neighborhood_ids':
                            neighborhoods[key]['id'] = param['value']
                            break

        return neighborhoods

    @staticmethod
    def _get_search_params(data):
        tab = data['explore_tabs'][0]
        pagination = tab['pagination_metadata']
        metadata = tab['home_tab_metadata']
        geography = metadata['geography']
        location = metadata['location']
        params = {
            'federated_search_session_id':
                data['metadata']['federated_search_session_id'],
            'last_search_session_id':
                pagination['search_session_id'],
            'place_id':
                geography['place_id'],
            'query':
                location['canonical_location']
        }

        return params

    def _parse_listing_contents(self, response):
        """Obtain data from an individual listing page."""
        xpath_match = response.xpath('//script[@id="data-state"]/text()').extract()[0]
        data = json.loads(xpath_match)
        listing = data['bootstrapData']['reduxData']['homePDP']['listingInfo']['listing']

        # item['person_capacity'] = listing['p3_event_data_logging']['person_capacity']
        item = DeepbnbItem(
            id=listing["id"],
            access=listing['sectioned_description']['access'],
            additional_house_rules=listing['additional_house_rules'],
            allows_events=listing['guest_controls']['allows_events'],
            amenities=','.join([la['name'] for la in listing['listing_amenities']]),
            business_travel_ready=listing['is_business_travel_ready'],
            city=listing['localized_city'],
            description=listing['sectioned_description']['summary'],
            host_id=listing['primary_host']['id'],
            # host_languages=listing['host_languages'],
            is_hotel=listing['is_hotel'],
            latitude=listing['lat'],
            longitude=listing['lng'],
            min_nights=listing['min_nights'],
            monthly_price_factor=self._data_cache[listing['id']]['monthly_price_factor'],
            name='=HYPERLINK("{}", "{}")'.format(response.url, listing.get('name', response.url)),
            # neighborhood=listing['neighborhood'],
            neighborhood_overview=listing['sectioned_description']['neighborhood_overview'],
            # new_listing=listing['is_new_listing'],
            notes=listing['sectioned_description']['notes'],
            person_capacity=listing['person_capacity'],
            price_rate=self._data_cache[listing["id"]]['price_rate'],
            price_rate_type=self._data_cache[listing["id"]]['price_rate_type'],
            # property_type=listing['property_type_id'],
            rating_accuracy=listing['p3_event_data_logging']['accuracy_rating'],
            rating_checkin=listing['p3_event_data_logging']['checkin_rating'],
            rating_cleanliness=listing['p3_event_data_logging']['cleanliness_rating'],
            rating_communication=listing['p3_event_data_logging']['communication_rating'],
            rating_location=listing['p3_event_data_logging']['location_rating'],
            rating_value=listing['p3_event_data_logging']['value_rating'],
            # refundable=listing['is_fully_refundable'],
            response_rate=listing['p3_event_data_logging']['response_rate_shown'],
            response_time=listing['p3_event_data_logging']['response_time_shown'],
            review_count=listing['review_details_interface']['review_count'],
            review_score=listing['review_details_interface']['review_score'],
            # reviews=listing['review_details_interface']['reviews'],
            room_type=listing['room_type_category'],
            satisfaction_guest=listing['p3_event_data_logging']['guest_satisfaction_overall'],
            star_rating=listing['star_rating'],
            # superhost=listing['is_superhost'],
            tier_id=listing['tier_id'],
            total_price=self._data_cache[listing['id']]['total_price'],
            url=response.url,
            user_id=listing['user']['id'],
            # user_name=listing['user']['first_name'],
            # verified=listing['verified_card'],
            weekly_price_factor=self._data_cache[listing['id']]['weekly_price_factor']
        )
        # if listing['price_interface']['cleaning_fee']:
        #     item['cleaning_fee'] = listing['price_interface']['cleaning_fee']['value']
        # item['house_rules'] = listing['house_rules']
        # item['price'] = listing['p3_event_data_logging']['price']
        # item['search_price'] = response.meta['search_price']
        # item['space'] = listing['space_interface']
        # item['summary'] = listing['summary']
        # item['reviews'] = data['bootstrapData']['reduxData']['homePDP'].get('reviewsInfo', {}).get(
        #     'cumulativeReviews')

        if 'calendar_last_updated_at' in listing:
            item['calendar_updated_at'] = listing['calendar_last_updated_at']

        if 'interaction' in listing['sectioned_description']:
            item['interaction'] = listing['sectioned_description']['interaction']

        return item
