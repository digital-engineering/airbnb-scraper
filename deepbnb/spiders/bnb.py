# -*- coding: utf-8 -*-
import json
import re
import scrapy

from datetime import date, timedelta
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from deepbnb.items import DeepbnbItem


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
            ne_lat=None,
            ne_lng=None,
            sw_lat=None,
            sw_lng=None,
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
        self._ids_seen = set()
        self._ne_lat = ne_lat
        self._ne_lng = ne_lng
        self._place = query
        self._search_params = {}
        self._set_price_params(max_price, min_price)
        self._sw_lat = sw_lat
        self._sw_lng = sw_lng

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

        # Handle pagination
        next_section = {}
        pagination = data['data']['dora']['exploreV3']['metadata']['paginationMetadata']
        if pagination['hasNextPage']:
            items_offset = pagination['itemsOffset']
            BnbSpider._add_search_params(next_section, response)
            next_section.update({'itemsOffset': items_offset})
            yield self._api_request(params=next_section, response=response)

        # handle listings
        params = {'_format': 'for_rooms_show', 'key': self._api_key}
        BnbSpider._add_search_params(params, response)
        listings = self._get_listings_from_sections(data['data']['dora']['exploreV3']['sections'])
        for listing in listings:  # request each property page
            listing_id = listing['listing']['id']
            if listing_id in self._ids_seen:
                continue  # filter duplicates
            self._ids_seen.add(listing_id)
            yield self._listing_api_request(listing, params)

    def parse_landing_page(self, response):
        """Parse search response and generate URLs for all searches, then perform them."""
        data = self.read_data(response)
        search_params = self._get_paginated_search_params(response, data)
        neighborhoods = self._get_neighborhoods(data)

        self._geography = data['data']['dora']['exploreV3']['metadata']['geography']

        self.logger.info(f"Geography:\n{self._geography}")
        self.logger.info(f"Neighborhoods:\n{neighborhoods}")

        yield self._api_request(params=search_params, response=response, callback=self.parse)

    def read_data(self, response):
        """Read response data as json"""
        self.logger.debug(f"Parsing {response.url}")
        data = json.loads(response.body)
        return data

    def start_requests(self):
        """Spider entry point. Generate the first search request(s)."""
        self.logger.info(f"starting survey for: {self._place}")

        # get params from injected constructor values
        params = {}
        if self._price_max:
            params['price_max'] = self._price_max

        if self._price_min:
            params['price_min'] = self._price_min

        if self._ne_lat:
            params['ne_lat'] = self._ne_lat

        if self._ne_lng:
            params['ne_lng'] = self._ne_lng

        if self._sw_lat:
            params['sw_lat'] = self._sw_lat

        if self._sw_lng:
            params['sw_lng'] = self._sw_lng

        if not self._checkin:  # assume not self._checkout also
            yield self._api_request(params, callback=self.parse_landing_page)

        checkin_range_spec, checkout_range_spec = self._process_checkin_vars()

        # perform request(s)
        yield from self._perform_checkin_start_requests(checkin_range_spec, checkout_range_spec, params)

    @staticmethod
    def _add_search_params(params, response):
        parsed_q = parse_qs(urlparse(response.request.url).query)
        if 'checkin' in parsed_q:
            params['checkin'] = parsed_q['checkin'][0]
            params['checkout'] = parsed_q['checkout'][0]

        if 'price_max' in parsed_q:
            params['price_max'] = parsed_q['price_max'][0]

        if 'price_min' in parsed_q:
            params['price_min'] = parsed_q['price_min'][0]

        if 'ne_lat' in parsed_q:
            params['ne_lat'] = parsed_q['ne_lat'][0]

        if 'ne_lng' in parsed_q:
            params['ne_lng'] = parsed_q['ne_lng'][0]

        if 'sw_lat' in parsed_q:
            params['sw_lat'] = parsed_q['sw_lat'][0]

        if 'sw_lng' in parsed_q:
            params['sw_lng'] = parsed_q['sw_lng'][0]

    def _api_request(self, params=None, response=None, callback=None):
        """Perform API request."""
        request = response.follow if response else scrapy.Request
        callback = callback or self.parse
        url = self._get_search_api_url(params)
        headers = self._get_search_headers()

        return request(url, callback, headers=headers)

    @staticmethod
    def _build_airbnb_url(path, query=None):
        if query is not None:
            query = urlencode(query)

        parts = ['https', 'www.airbnb.com', path, None, query, None]
        return urlunparse(parts)

    @staticmethod
    def _build_date_range(iso_date: str, range_spec: str):
        """Calculate start and end dates for a range. Return start date and timedelta for number of days."""
        base_date = date.fromisoformat(iso_date)
        if range_spec.startswith('+-'):  # +-7
            days = float(re.match(r'\+\-(\d+)', range_spec).group(1))
            start_date = base_date - timedelta(days=days)
            end_date = base_date + timedelta(days=days)
        else:  # +0-3
            result = re.match(r'\+(\d+)\-(\d+)', range_spec)
            post_days = float(result.group(1))
            pre_days = float(result.group(2))
            start_date = base_date - timedelta(days=pre_days)
            end_date = base_date + timedelta(days=post_days)
        return start_date, end_date - start_date

    def _get_listings_from_sections(self, sections):
        """Get listings from sections, also collect some data and save it for later. Double check prices are correct,
        because airbnb switches to """
        listings = []
        for section in [s for s in sections if s['sectionComponentType'] == 'listings_ListingsGrid_Explore']:
            for listing in section.get('items'):
                listing_id = listing['listing']['id']
                pricing = listing['pricingQuote']
                rate_with_service_fee = pricing['rateWithServiceFee']['amount']

                # To account for results where price_max was specified as monthly but quoted rate is nightly, calculate
                # monthly rate and drop listing if it is greater. Use 28 days = 1 month. Assume price_max of 1000+ is a
                # monthly price requirement.
                if (self._price_max and self._price_max > 1000
                        and pricing['rate_type'] != 'monthly'
                        and (rate_with_service_fee * 28) > self._price_max):
                    continue

                self._data_cache[listing_id] = {}
                self._data_cache[listing_id]['monthly_price_factor'] = pricing['monthlyPriceFactor']
                self._data_cache[listing_id]['weekly_price_factor'] = pricing['weeklyPriceFactor']

                if self._checkin:  # use total price if dates given, price rate otherwise
                    self._data_cache[listing_id]['price_rate'] = pricing['rateWithServiceFee']['amount']
                    self._data_cache[listing_id]['price_rate_type'] = pricing['rateType']
                    self._data_cache[listing_id]['total_price'] = pricing['price']['total']['amount']
                else:
                    self._data_cache[listing_id]['price_rate'] = pricing['rateWithServiceFee']['amount']
                    self._data_cache[listing_id]['price_rate_type'] = pricing['rateType']
                    self._data_cache[listing_id]['total_price'] = None  # can't show total price if there are no dates

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

    @staticmethod
    def _get_paginated_search_params(response, data):
        """Consolidate search parameters and return result."""
        metadata = data['data']['dora']['exploreV3']['metadata']
        pagination = metadata['paginationMetadata']
        filter_state = data['data']['dora']['exploreV3']['filters']['state']
        place_id = metadata['geography']['placeId']
        query = [fs['value']['stringValue'] for fs in filter_state if fs['key'] == 'query'][0]
        params = {
            'searchSessionId': pagination['searchSessionId'],
            'place_id':        place_id,
            'query':           query
        }

        if pagination['has_next_page']:
            params['last_search_session_id'] = pagination['search_session_id']

        BnbSpider._add_search_params(params, response)

        return params

    def _get_search_api_url(self, params=None):
        _api_path = '/api/v3/ExploreSearch'

        query = {
            'operationName': 'ExploreSearch',
            'locale':        'en',
            'currency':      'USD',
            'variables':     {
                "request": {
                    "metadataOnly":          False,
                    "version":               "1.7.9",
                    "itemsPerGrid":          20,
                    "tabId":                 "home_tab",
                    "refinementPaths":       ["/homes"],
                    "placeId":               "ChIJ66UNqQ_q9kARqrR19TYkx8A",
                    "source":                "search_blocks_selector_p1_flow",
                    "searchType":            "search_query",
                    "query":                 self._place,
                    "cdnCacheSafe":          False,
                    "simpleSearchTreatment": "simple_search_only",
                    "treatmentFlags":        [
                        "simple_search_1_1",
                        "flexible_dates_options_extend_one_three_seven_days"
                    ],
                    "screenSize":            "small"
                }
            },
            'extensions':    {
                "persistedQuery": {
                    "version":    1,
                    "sha256Hash": "13aa9971e70fbf5ab888f2a851c765ea098d8ae68c81e1f4ce06e2046d91b6ea"
                }
            },
            '_cb':           '8wv88gb4e4gw'
        }

        if params:
            query.update(params)

        if self.settings.get('PROPERTY_AMENITIES'):
            amenities = self.settings.get('PROPERTY_AMENITIES').values()
            query = list(query.items())  # convert dict to list of tuples because we need multiple identical keys
            for a in amenities:
                query.append(('amenities[]', a))

        url = self._build_airbnb_url(_api_path, query)
        return url

    def _get_search_headers(self):
        """Get headers for search requests."""
        if self._api_key is None:
            self._api_key = self.settings.get('AIRBNB_API_KEY')

        return {
            'Content-Type':                     'application/json',
            'Device-Memory':                    8,
            'DPR':                              '2.625',
            'ect':                              '4g',
            'Referer':                          'https://www.airbnb.com/',
            'User-Agent':                       'Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Mobile Safari/537.36',
            'Viewport-Width':                   1180,
            'X-Airbnb-API-Key':                 self._api_key,
            'X-Airbnb-GraphQL-Platform':        'web',
            'X-Airbnb-GraphQL-Platform-Client': 'minimalist-niobe',
            'X-CSRF-Token':                     'V4$.airbnb.com$88klQ0-SkSk$f0wWUrY3M_I37iPj33S8w3-shUgkwi4Dq63e19JPlGQ=',
            'X-CSRF-Without-Token':             1,
        }

    def _listing_api_request(self, listing, params):
        """Generate scrapy.Request for listing page."""
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
            amenities=[la['name'] for la in listing['listing_amenities'] if la['is_present']],
            amenity_ids=[la['id'] for la in listing['listing_amenities'] if la['is_present']],
            bathrooms=listing.get('bathrooms', re.search(r'\d+(\.\d+)?', listing['bathroom_label'])[0]),
            bedrooms=self._parse_bedrooms(listing),
            beds=listing.get('beds', re.search(r'\d+', listing['bed_label'])[0]),
            business_travel_ready=listing['is_business_travel_ready'],
            city=listing.get('localized_city', self._geography['city']),
            country=self._geography['country'],
            country_code=listing.get('country_code', self._geography['country_code']),
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
            photos=listing['photos'],
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

    def _perform_checkin_start_requests(self, checkin_range_spec: str, checkout_range_spec: str, params: dict):
        """Perform requests for start URLs.

        :param checkin_range_spec:
        :param checkout_range_spec:
        :param params:
        :return:
        """
        # single request for static start and end dates
        if not (checkin_range_spec or checkout_range_spec):  # simple start and end date
            params['checkin'] = self._checkin
            params['checkout'] = self._checkout
            yield self._api_request(params, callback=self.parse_landing_page)

        # multi request for dynamic start and static end date
        if checkin_range_spec and not checkout_range_spec:  # ranged start date, single end date, iterate over checkin range
            checkin_start_date, checkin_range = self._build_date_range(self._checkin, checkin_range_spec)
            for i in range(checkin_range.days + 1):  # + 1 to include end date
                params['checkin'] = self._checkin = str(checkin_start_date + timedelta(days=i))
                params['checkout'] = self._checkout
                yield self._api_request(params, callback=self.parse_landing_page)

        # multi request for static start and dynamic end date
        if checkout_range_spec and not checkin_range_spec:  # ranged end date, single start date, iterate over checkout range
            checkout_start_date, checkout_range = self._build_date_range(self._checkout, checkout_range_spec)
            for i in range(checkout_range.days + 1):  # + 1 to include end date
                params['checkout'] = self._checkout = str(checkout_start_date + timedelta(days=i))
                params['checkin'] = self._checkin
                yield self._api_request(params, callback=self.parse_landing_page)

        # double nested multi request, iterate over both start and end date ranges
        if checkout_range_spec and checkin_range_spec:
            checkin_start_date, checkin_range = self._build_date_range(self._checkin, checkin_range_spec)
            checkout_start_date, checkout_range = self._build_date_range(self._checkout, checkout_range_spec)
            for i in range(checkin_range.days + 1):  # + 1 to include end date
                params['checkin'] = self._checkin = str(checkin_start_date + timedelta(days=i))
                for j in range(checkout_range.days + 1):  # + 1 to include end date
                    params['checkout'] = self._checkout = str(checkout_start_date + timedelta(days=j))
                    yield self._api_request(params, callback=self.parse_landing_page)

    def _process_checkin_vars(self) -> tuple:
        """Determine if a range is specified, if so, extract ranges and return as variables.

        @NOTE: Should only be run once on crawler initialization.

        :return: checkin/checkout range specs
        """
        if not self._checkin:
            return None, None

        checkin_range_spec, checkout_range_spec = None, None

        checkin_plus_range_position = self._checkin.find('+')
        if checkin_plus_range_position != -1:  # range_spec e.g. +5-3 means plus five days, minus three days
            checkin_range_spec = self._checkin[checkin_plus_range_position:]
            self._checkin = self._checkin[:checkin_plus_range_position]

        checkout_plus_range_position = self._checkout.find('+')
        if checkout_plus_range_position != -1:  # range_spec e.g. +-3 means plus or minus 3 days
            checkout_range_spec = self._checkout[checkout_plus_range_position:]
            self._checkout = self._checkout[:checkout_plus_range_position]

        return checkin_range_spec, checkout_range_spec

    def _set_price_params(self, price_max, price_min):
        """Set price parameters based on price_max and price_min input values."""
        self._price_max = price_max
        self._price_min = price_min
        if self._price_min and self._price_max:
            self._price_max = int(self._price_max)
            self._price_min = int(self._price_min)
            self.price_range = (self._price_min, self._price_max, self.default_price_increment)

        if self._price_min and not self._price_max:
            self._price_min = int(self._price_min)
            self.price_range = (self._price_min, self.default_max_price, self.default_price_increment)

        if not self._price_min and self._price_max:
            self._price_max = int(self._price_max)
            self.price_range = (0, self._price_max, self.default_price_increment)
