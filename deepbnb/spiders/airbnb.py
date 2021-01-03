# -*- coding: utf-8 -*-
import json
import lxml.html
import re
import scrapy

from typing import Union

from deepbnb.items import DeepbnbItem
from deepbnb.api.ExploreSearch import ExploreSearch
from deepbnb.api.PdpPlatformSections import PdpPlatformSections
from deepbnb.api.PdpReviews import PdpReviews


class AirbnbSpider(scrapy.Spider):
    """Airbnb Spider

    Perform a search, collect data from search results, cache that data, then scrape each listing individually to
    obtain additional information, and finally compile the data together into a DeepbnbItem.
    """

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
        self._pdp_reviews = None
        self._place = query
        self._regex_amenity_id = re.compile(r'^([a-z0-9]+_)+([0-9]+)_')
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

    @property
    def geography(self):
        return self._geography

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
        params = {'key': self._explore_search.api_key}
        self._explore_search.add_search_params(params, response)
        listing_ids = self._get_listings_from_sections(data['data']['dora']['exploreV3']['sections'])
        for listing_id in listing_ids:  # request each property page
            if listing_id in self._ids_seen:
                continue  # filter duplicates

            self._ids_seen.add(listing_id)

            yield self._pdp_platform_sections.api_request(listing_id)

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

    def parse_listing_contents(self, response):
        """Obtain data from an individual listing page, combine with cached data, and return DeepbnbItem."""
        # Collect base data
        data = self.read_data(response)
        pdp_sections = data['data']['merlin']['pdpSections']
        listing_id = pdp_sections['id']
        sections = pdp_sections['sections']
        metadata = pdp_sections['metadata']

        logging_data = metadata['loggingContext']['eventDataLogging']

        # Get sections
        amenities_section = [s for s in sections if s['sectionId'] == 'AMENITIES_DEFAULT'][0]['section']
        description_section = [s for s in sections if s['sectionId'] == 'DESCRIPTION_DEFAULT'][0]['section']
        host_profile = [s for s in sections if s['sectionId'] == 'HOST_PROFILE_DEFAULT'][0]['section']
        location = [s for s in sections if s['sectionId'] == 'LOCATION_DEFAULT'][0]['section']
        policies = [s for s in sections if s['sectionId'] == 'POLICIES_DEFAULT'][0]['section']

        # Collect amenity data
        amenities_groups = amenities_section['seeAllAmenitiesGroups']
        amenities_access = [g['amenities'] for g in amenities_groups if g['title'] == 'Guest access']
        amenities_avail = [amenity for g in amenities_groups for amenity in g['amenities'] if amenity['available']]

        # Structure data
        listing_data_cached = self._data_cache[listing_id]
        item = DeepbnbItem(
            id=listing_id,
            access=self._render_titles(amenities_access[0]) if amenities_access else None,
            additional_house_rules=policies['additionalHouseRules'],
            allows_events='No parties or events' in [r['title'] for r in policies['houseRules']],
            amenities=self._render_titles(amenities_avail, sep=' - ', join=False),
            amenity_ids=list(self._get_amenity_ids(amenities_avail)),
            avg_rating=listing_data_cached['avg_rating'],
            bathrooms=listing_data_cached['bathrooms'],
            bedrooms=listing_data_cached['bedrooms'],
            beds=listing_data_cached['beds'],
            business_travel_ready=listing_data_cached['business_travel_ready'],
            city=listing_data_cached.get('city', self._geography['city']),
            country=self._geography['country'],
            description=self._html_to_text(description_section['htmlDescription']['htmlText']),
            host_id=listing_data_cached['host_id'],
            house_rules=[r['title'] for r in policies['houseRules']],
            is_hotel=metadata['bookingPrefetchData']['isHotelRatePlanEnabled'],
            latitude=listing_data_cached['latitude'],
            listing_expectations=self._render_titles(policies['listingExpectations']) if policies else None,
            longitude=listing_data_cached['longitude'],
            # max_nights=listing.get('max_nights'),
            # min_nights=listing['min_nights'],
            monthly_price_factor=listing_data_cached['monthly_price_factor'],
            name=listing_data_cached.get('name', listing_id),
            neighborhood_overview=listing_data_cached.get('neighborhood_overview'),
            # notes=listing['sectioned_description']['notes'],
            person_capacity=listing_data_cached['person_capacity'],
            photo_count=listing_data_cached['photo_count'],
            photos=listing_data_cached['photos'],
            place_id=self._geography['placeId'],
            price_rate=listing_data_cached['price_rate'],
            price_rate_type=listing_data_cached['price_rate_type'],
            province=self._geography.get('province'),
            rating_accuracy=logging_data['accuracyRating'],
            rating_checkin=logging_data['checkinRating'],
            rating_cleanliness=logging_data['cleanlinessRating'],
            rating_communication=logging_data['communicationRating'],
            rating_location=logging_data['locationRating'],
            rating_value=logging_data['valueRating'],
            review_count=listing_data_cached['review_count'],
            reviews=self._pdp_reviews.api_request(listing_id, 50),
            room_and_property_type=listing_data_cached['room_and_property_type'],
            room_type=listing_data_cached['room_type'],
            room_type_category=listing_data_cached['room_type_category'],
            satisfaction_guest=logging_data['guestSatisfactionOverall'],
            star_rating=listing_data_cached['star_rating'],
            state=self._geography['state'],
            # summary=listing['sectioned_description']['summary'],
            total_price=listing_data_cached['total_price'],
            url="https://www.airbnb.com/rooms/{}".format(listing_id),
            weekly_price_factor=listing_data_cached['weekly_price_factor']
        )

        self._get_detail_property(item, 'transit', 'Getting around', location['seeAllLocationDetails'], 'content')
        self._get_detail_property(item, 'interaction', 'During your stay', host_profile['hostInfos'], 'html')

        return item

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
        self._pdp_reviews = PdpReviews(self.settings.get('AIRBNB_API_KEY'), self)

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

        if self._checkin:  # assume self._checkout also
            checkin_range_spec, checkout_range_spec = self._process_checkin_vars()
            yield from self._explore_search.perform_checkin_start_requests(
                checkin_range_spec, checkout_range_spec, params)
        else:
            yield self._explore_search.api_request(self._place, params, callback=self.parse_landing_page)

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
    def _html_to_text(html: str) -> str:
        """Get plaintext from HTML."""
        return lxml.html.document_fromstring(html).text_content()

    @staticmethod
    def _render_titles(title_list: list, sep: str = ': ', join=True) -> Union[str, list]:
        """Render list of objects with titles and subtitles into string."""
        lines = []
        for t in title_list:
            line = '{}{}{}'.format(t['title'], sep, t['subtitle']) if t.get('subtitle') else t.get('title')
            lines.append(line)

        return '\n'.join(lines) if join else lines

    def _collect_listing_data(self, listing_item: dict):
        """Collect listing data from search results, save in _data_cache. All listing data is aggregated together in the
        parse_listing_contents method."""
        listing = listing_item['listing']
        pricing = listing_item['pricingQuote']

        self._data_cache[listing['id']] = {
            # get general data
            'avg_rating':             listing['avgRating'],
            'bathrooms':              listing['bathrooms'],
            'bedrooms':               listing['bedrooms'],
            'beds':                   listing['beds'],
            'business_travel_ready':  listing['isBusinessTravelReady'],
            'host_id':                listing['user']['id'],
            'latitude':               listing['lat'],
            'longitude':              listing['lng'],
            'name':                   listing['name'],
            'neighborhood_overview':  listing['neighborhoodOverview'],
            'person_capacity':        listing['personCapacity'],
            'photo_count':            listing['pictureCount'],
            'photos':                 [p['picture'] for p in listing['contextualPictures']],
            'review_count':           listing['reviewsCount'],
            'room_and_property_type': listing['roomAndPropertyType'],
            'room_type':              listing['roomType'],
            'room_type_category':     listing['roomTypeCategory'],
            'star_rating':            listing['starRating'],

            # get pricing data
            'monthly_price_factor':   pricing['monthlyPriceFactor'],
            'weekly_price_factor':    pricing['weeklyPriceFactor'],
            'price_rate':             pricing['rateWithServiceFee']['amount'],
            'price_rate_type':        pricing['rateType'],
            # use total price if dates given, price rate otherwise. can't show total price if there are no dates.
            'total_price':            pricing['price']['total']['amount'] if self._checkin else None
        }

    def _get_amenity_ids(self, amenities: list):
        """Extract amenity id from `id` string field."""
        for amenity in amenities:
            match = self._regex_amenity_id.match(amenity['id'])
            amenity_id = int(match.group(match.lastindex))
            yield amenity_id

    def _get_listings_from_sections(self, sections: list) -> list:
        """Get listings from sections, also collect some data and save it for later. Double check prices are correct,
        because airbnb switches to daily pricing if less than 28 days are selected (during a range search)."""
        listing_ids = []
        for section in [s for s in sections if s['sectionComponentType'] == 'listings_ListingsGrid_Explore']:
            for listing_item in section.get('items'):
                pricing = listing_item['pricingQuote']
                rate_with_service_fee = pricing['rateWithServiceFee']['amount']

                # To account for results where price_max was specified as monthly but quoted rate is nightly, calculate
                # monthly rate and drop listing if it is greater. Use 28 days = 1 month. Assume price_max of 1000+ is a
                # monthly price requirement.
                if (self._price_max and self._price_max > 1000
                        and pricing['rate_type'] != 'monthly'
                        and (rate_with_service_fee * 28) > self._price_max):
                    continue

                self._collect_listing_data(listing_item)
                listing_ids.append(listing_item['listing']['id'])

        return listing_ids

    def _get_detail_property(self, item, prop, title, prop_list, key):
        """Search for matching title in property list for prop. If exists, add htmlText for key to item."""
        if title in [i['title'] for i in prop_list]:
            item[prop] = self._html_to_text([i[key]['htmlText'] for i in prop_list if i['title'] == title][0])

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
