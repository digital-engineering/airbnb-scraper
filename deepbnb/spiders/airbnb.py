# -*- coding: utf-8 -*-
import json
import scrapy

from deepbnb.items import DeepbnbItem
from deepbnb.api.ExploreSearch import ExploreSearch
from deepbnb.api.PdpPlatformSections import PdpPlatformSections


class AirbnbSpider(scrapy.Spider):
    name = 'airbnb'
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
        self._explore_search = None
        self._pdp_platform_sections = None
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

    def parse(self, response, **kwargs):
        """Default parse method."""
        data = self.read_data(response)

        # Handle pagination
        next_section = {}
        pagination = data['data']['dora']['exploreV3']['metadata']['paginationMetadata']
        if pagination['hasNextPage']:
            items_offset = pagination['itemsOffset']
            self._explore_search.add_search_params(next_section, response)
            next_section.update({'itemsOffset': items_offset})

            yield self._explore_search.api_request(place=self._place, params=next_section, response=response)

        # handle listings
        # params = {'_format': 'for_rooms_show', 'key': self._api_key}
        params = {'key': self._explore_search._api_key}
        self._explore_search.add_search_params(params, response)
        listings = self._get_listings_from_sections(data['data']['dora']['exploreV3']['sections'])
        for listing in listings:  # request each property page
            listing_id = listing['listing']['id']
            if listing_id in self._ids_seen:
                continue  # filter duplicates

            self._ids_seen.add(listing_id)

            yield self._pdp_platform_sections.listing_api_request(listing)

    def parse_landing_page(self, response):
        """Parse search response and generate URLs for all searches, then perform them."""
        data = self.read_data(response)
        search_params = self._explore_search.get_paginated_search_params(response, data)
        # neighborhoods = self._get_neighborhoods(data)

        self._geography = data['data']['dora']['exploreV3']['metadata']['geography']

        self.logger.info(f"Geography:\n{self._geography}")
        # self.logger.info(f"Neighborhoods:\n{neighborhoods}")

        yield self._explore_search.api_request(
            place=self._place, params=search_params, response=response, callback=self.parse)

    def read_data(self, response):
        """Read response data as json"""
        self.logger.debug(f"Parsing {response.url}")
        data = json.loads(response.body)

        return data

    def start_requests(self):
        """Spider entry point. Generate the first search request(s)."""
        self.logger.info(f"starting survey for: {self._place}")

        self._explore_search = ExploreSearch(self.settings.get('AIRBNB_API_KEY'), self)
        self._pdp_platform_sections = PdpPlatformSections(self.settings.get('AIRBNB_API_KEY'), self)

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
            yield self._explore_search.api_request(self._place, params, callback=self.parse_landing_page)

        checkin_range_spec, checkout_range_spec = self._process_checkin_vars()

        # perform request(s)
        yield from self._explore_search.perform_checkin_start_requests(checkin_range_spec, checkout_range_spec, params)

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

                # get general data
                self._data_cache[listing_id]['amenities'] = listing['previewAmenityNames']
                self._data_cache[listing_id]['amenity_ids'] = listing['amenityIds']

                self._data_cache[listing_id]['bathrooms'] = listing['bathrooms']
                self._data_cache[listing_id]['bedrooms'] = listing['bedrooms']
                self._data_cache[listing_id]['beds'] = listing['beds']

                self._data_cache[listing_id]['business_travel_ready'] = listing['isBusinessTravelReady']

                self._data_cache[listing_id]['latitude'] = listing['lat']
                self._data_cache[listing_id]['longitude'] = listing['lng']

                # get pricing data
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

    def parse_listing_contents(self, response):
        """Obtain data from an individual listing page."""
        data = self.read_data(response)
        sections = data['data']['merlin']['pdpSections']['sections']
        policies = [s for s in sections if s['sectionId'] == 'POLICIES_DEFAULT'][0]
        listing_id = data['data']['merlin']['pdpSections']['id']
        listing_data_cached = self._data_cache[listing_id]
        item = DeepbnbItem(
            id=listing_id,
            # access=listing['sectioned_description']['access'],
            additional_house_rules=policies['additionalHouseRules'],
            # allows_events=listing['guest_controls']['allows_events'],
            amenities=listing_data_cached['amenities'],
            amenity_ids=listing_data_cached['amenity_ids'],
            bathrooms=listing_data_cached['bathrooms'],
            bedrooms=listing_data_cached['bedrooms'],
            beds=listing_data_cached['beds'],
            business_travel_ready=listing_data_cached['business_travel_ready'],
            city=listing_data_cached.get('city', self._geography['city']),
            country=self._geography['country'],
            # country_code=listing.get('country_code', self._geography['country_code']),
            description=listing['sectioned_description']['description'],
            host_id=listing['primary_host']['id'],
            house_rules=listing['sectioned_description']['house_rules'],
            is_hotel=listing['is_hotel'],
            latitude=listing_data_cached['latitude'],
            longitude=listing_data_cached['longitude'],
            max_nights=listing.get('max_nights'),
            min_nights=listing['min_nights'],
            monthly_price_factor=listing_data_cached['monthly_price_factor'],
            name=listing.get('name', listing_id),
            neighborhood_overview=listing['sectioned_description']['neighborhood_overview'],
            notes=listing['sectioned_description']['notes'],
            person_capacity=listing['person_capacity'],
            photo_count=len(listing['photos']),
            photos=listing['photos'],
            place_id=self._geography['place_id'],
            price_rate=listing_data_cached['price_rate'],
            price_rate_type=listing_data_cached['price_rate_type'],
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
            total_price=listing_data_cached['total_price'],
            transit=listing['sectioned_description']['transit'],
            url="https://www.airbnb.com/rooms/{}".format(listing_id),
            weekly_price_factor=listing_data_cached['weekly_price_factor']
        )

        if 'interaction' in listing['sectioned_description'] and listing['sectioned_description']['interaction']:
            item['interaction'] = listing['sectioned_description']['interaction']

        return item

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
