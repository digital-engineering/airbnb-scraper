import json
import re
import scrapy

from datetime import date, timedelta
from scrapy.http import HtmlResponse
from scrapy_playwright.page import PageMethod

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
        self.__checkin = checkin
        self.__checkout = checkout
        self.__currency = currency
        self.__data_cache = {}
        self.__explore_search = None
        self.__geography = {}
        self.__ids_seen = set()
        self.__ne_lat = ne_lat
        self.__ne_lng = ne_lng
        self.__pdp_platform_sections = None
        self.__pdp_reviews = None
        self.__query = query
        self.__search_params = {}
        self.__set_price_params(max_price, min_price)
        self.__sw_lat = sw_lat
        self.__sw_lng = sw_lng

    def start_requests(self):
        """Spider entry point. Generate the first search request(s)."""
        self.logger.info(f'starting survey for: {self.__query}')
        if 'deepbnb.pipelines.ElasticBnbPipeline' in self.settings.get('ITEM_PIPELINES'):
            self.__create_index_if_not_exists()

        api_key = self.settings.get('AIRBNB_API_KEY')
        self.__explore_search = ExploreSearch(
            api_key,
            self.logger,
            self.__currency,
            self,
            self.settings.get('ROOM_TYPES'),
            self.__geography,
            self.__query
        )
        self.__pdp_platform_sections = PdpPlatformSections(
            api_key,
            self.logger,
            self.__currency,
            self.__data_cache,
            self.__geography,
            PdpReviews(api_key, self.logger, self.__currency)
        )

        # get params from injected constructor values
        params = {}
        if self.__price_max:
            params['priceMax'] = self.__price_max

        if self.__price_min:
            params['priceMin'] = self.__price_min

        if self.__ne_lat:
            params['ne_lat'] = self.__ne_lat

        if self.__ne_lng:
            params['ne_lng'] = self.__ne_lng

        if self.__sw_lat:
            params['sw_lat'] = self.__sw_lat

        if self.__sw_lng:
            params['sw_lng'] = self.__sw_lng

        if self.__checkin:  # assume self._checkout also
            checkin, checkout, checkin_range_spec, checkout_range_spec = self._process_checkin_vars()
            yield from self.__explore_search.perform_checkin_start_requests(
                checkin, checkout, checkin_range_spec, checkout_range_spec, params)
        else:
            search_path = self.__query.replace(', ', '--').replace(' ', '-') + '/homes'
            url = self.__explore_search.build_airbnb_url('s/' + search_path)

            yield scrapy.Request(url, self.parse_landing_page, headers={
                'accept':                    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'accept-encoding':           'gzip, deflate, br',
                'accept-language':           'en-US,en;q=0.9',
                'cache-control':             'no-cache',
                'pragma':                    'no-cache',
                'sec-ch-ua':                 '"Not;A=Brand";v="99", "Chromium";v="106"',
                'sec-ch-ua-mobile':          '?0',
                'sec-ch-ua-platform':        '"Linux"',
                'sec-fetch-dest':            'document',
                'sec-fetch-mode':            'navigate',
                'sec-fetch-site':            'none',
                'sec-fetch-user':            '?1',
                'upgrade-insecure-requests': '1',
                'user-agent':                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
            }, meta={
                'playwright':              True,
                'playwright_include_page': True,
                'playwright_page_methods': [PageMethod('wait_for_selector', '#data-deferred-state', state='hidden')]
            }, errback=self.errback)

    async def errback(self, failure):
        page = failure.request.meta['playwright_page']
        await page.close()

    async def parse_landing_page(self, response: HtmlResponse):
        """Parse search response and generate URLs for all searches, then perform them."""
        # debugging: get data from all script data-* attributes
        # script_data = {s.attrib['id']: json.loads(s.css('::text').get()) for s in response.css('script[id^=data-]')}
        data_deferred = json.loads(response.xpath('//script[@id="data-deferred-state"]/text()').get())
        data_deferred['niobeMinimalClientData'][0][0] = json.loads(
            re.sub(r'^StaysSearch:', '', data_deferred['niobeMinimalClientData'][0][0]))

        explore_data = data_deferred['niobeMinimalClientData'][0][1]['data']['presentation']['explore']
        if 'sectionIndependentData' in explore_data['sections']:
            stays_search = explore_data['sections']['sectionIndependentData']['staysSearch']
            remarketing_data = stays_search['loggingMetadata']['remarketingLoggingData']
            listing_data = stays_search['searchResults']
        else:
            remarketing_data = self.__find_section(explore_data['sections']['sections'], 'EXPLORE_REMARKETING')
            listing_data_wrapper = self.__find_section(explore_data['sections']['sections'], 'EXPLORE_SECTION_WRAPPER')
            listing_data = listing_data_wrapper['child']['section']

        self.__geography.update({k: v for k, v in remarketing_data.items() if k in ['city', 'country', 'state']})
        self.logger.info(f"Geography:\n{self.__geography}")

        cookie = response.headers.get('Set-Cookie')  # maybe use this later?

        # Should we query ExploreSearch and get some additional information first, as the page itself does? For instance,
        # this may be the way to get place_id

        search_params = {}
        yield self.__explore_search.api_request(self.__query, search_params, self.__explore_search.parse_landing_page)

    def parse(self, response, **kwargs):
        """Default parse method."""
        data = self.__explore_search.read_data(response)

        # Handle pagination
        next_section = {}
        pagination = data['data']['dora']['exploreV3']['metadata']['paginationMetadata']
        if pagination['hasNextPage']:
            items_offset = pagination['itemsOffset']
            self.__explore_search.add_search_params(next_section, response)
            next_section.update({'itemsOffset': items_offset})

            yield self.__explore_search.api_request(self.__query, next_section, response=response)

        # handle listings
        params = {'key': self.__explore_search.api_key}
        self.__explore_search.add_search_params(params, response)
        listing_ids = self.__get_listings_from_sections(data['data']['dora']['exploreV3']['sections'])
        for listing_id in listing_ids:  # request each property page
            if listing_id in self.__ids_seen:
                continue  # filter duplicates

            self.__ids_seen.add(listing_id)

            yield self.__pdp_platform_sections.api_request(listing_id)

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

    def _collect_listing_data(self, listing_item: dict):
        """Collect listing data from search results, save in _data_cache. All listing data is aggregated together in the
        parse_listing_contents method."""
        listing = listing_item['listing']
        pricing = listing_item['pricingQuote'] or {}

        self.__data_cache[listing['id']] = {
            # get general data
            'avg_rating':             listing['avgRating'],
            'bathrooms':              listing['bathrooms'],
            'bedrooms':               listing['bedrooms'],
            'beds':                   listing['beds'],
            'business_travel_ready':  listing['isBusinessTravelReady'],
            'city':                   listing['city'],
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
            'monthly_price_factor':   pricing.get('monthlyPriceFactor'),
            'weekly_price_factor':    pricing.get('weeklyPriceFactor'),
            'price_rate':             self.__get_price_rate(pricing),
            'price_rate_type':        self.__get_rate_type(pricing),
            # use total price if dates given, price rate otherwise. can't show total price if there are no dates.
            'total_price':            self.__get_total_price(pricing)
        }

    def __create_index_if_not_exists(self):
        index_name = self.settings.get('ELASTICSEARCH_INDEX')
        # index = Index(index_name)
        # if not index.exists():
        #     Listing.init(index_name)

    def __get_listings_from_sections(self, sections: list) -> list:
        """Get listings from "sections" (i.e. search results page sections).

         Also collect some data and save it for later. Double check prices are correct, because Airbnb switches to daily
         pricing if less than 28 days are selected (e.g. during a range search).
        """
        listing_ids = []
        for section in [s for s in sections if s['sectionComponentType'] == 'listings_ListingsGrid_Explore']:
            for listing_item in section.get('items'):
                pricing = listing_item['pricingQuote']
                if pricing:
                    rate_with_service_fee = pricing['rateWithServiceFee']
                    if rate_with_service_fee is None:  # some properties need dates to show rates
                        rate_with_service_fee_amt = 0
                        pricing['rateWithServiceFee'] = {'amount': None}
                    else:
                        rate_with_service_fee_amt = rate_with_service_fee['amount']

                    # To account for results where price_max was specified as monthly but quoted rate is nightly, calculate
                    # monthly rate and drop listing if it is greater. Use 28 days = 1 month. Assume price_max of 1000+ is a
                    # monthly price requirement.
                    if (self.__price_max and self.__price_max > 1000
                            and pricing['structuredStayDisplayPrice']['primaryLine']['qualifier'] != 'month'
                            and (rate_with_service_fee_amt * 28) > self.__price_max):
                        continue

                self._collect_listing_data(listing_item)
                listing_ids.append(listing_item['listing']['id'])

        return listing_ids

    @staticmethod
    def __get_price_key(pricing) -> str:
        return 'price' if 'price' in pricing['structuredStayDisplayPrice']['primaryLine'] else 'discountedPrice'

    @staticmethod
    def __get_price_rate(pricing) -> int | None:
        if pricing:
            price_key = AirbnbSpider.__get_price_key(pricing)
            return int(pricing['structuredStayDisplayPrice']['primaryLine'][price_key].lstrip('$').replace(',', ''))

        return None

    @staticmethod
    def __get_rate_type(pricing) -> str | None:
        if pricing:
            return pricing['structuredStayDisplayPrice']['primaryLine']['qualifier']

        return None

    def __get_total_price(self, pricing) -> int | None:
        if not self.__checkin:
            return None  # can't have a price without dates

        if pricing['structuredStayDisplayPrice']['secondaryLine']:
            price = pricing['structuredStayDisplayPrice']['secondaryLine']['price']
            amount_match = re.match(r'\$([\w,]+) total', price)
        else:
            price_key = AirbnbSpider.__get_price_key(pricing)
            price = pricing['structuredStayDisplayPrice']['primaryLine'][price_key]
            amount_match = re.match(r'\$([\w,]+)', price)

        if not amount_match:
            raise ValueError('No amount match found for price: %s' % price)

        return int(amount_match[1].replace(',', ''))

    @staticmethod
    def __find_section(sections: list, section_type: str):
        result = [i for i in sections if i.get('sectionComponentType') == section_type]
        return result.pop().get('section') if result else {}

    def _process_checkin_vars(self) -> tuple:
        """Determine if a range is specified, if so, extract ranges, validate, and return as variables.

        @NOTE: Should only be run once on crawler initialization.

        :return: checkin/checkout range specs
        """
        if not self.__checkin:
            return None, None, None, None

        checkin_range_spec, checkout_range_spec = None, None

        # Handle ranged queries
        checkin_plus_range_position = self.__checkin.find('+')
        if checkin_plus_range_position != -1:  # range_spec e.g. +5-3 means plus five days, minus three days
            checkin_range_spec = self.__checkin[checkin_plus_range_position:]
            self.__checkin = self.__checkin[:checkin_plus_range_position]

        checkout_plus_range_position = self.__checkout.find('+')
        if checkout_plus_range_position != -1:  # range_spec e.g. +-3 means plus or minus 3 days
            checkout_range_spec = self.__checkout[checkout_plus_range_position:]
            self.__checkout = self.__checkout[:checkout_plus_range_position]

        # Validate checkin / checkout values
        today = date.today()
        if date.fromisoformat(self.__checkin) < today:
            raise ValueError('Checkin cannot be in past: {}'.format(self.__checkin))
        tomorrow = today + timedelta(days=1)
        if date.fromisoformat(self.__checkout) < tomorrow:
            raise ValueError('Checkout must be tomorrow or later: {}'.format(self.__checkout))

        return self.__checkin, self.__checkout, checkin_range_spec, checkout_range_spec

    def __set_price_params(self, price_max, price_min):
        """Set price parameters based on price_max and price_min input values."""
        self.__price_max = price_max
        self.__price_min = price_min
        if self.__price_min and self.__price_max:
            self.__price_max = int(self.__price_max)
            self.__price_min = int(self.__price_min)
            self.price_range = (self.__price_min, self.__price_max, self.default_price_increment)

        if self.__price_min and not self.__price_max:
            self.__price_min = int(self.__price_min)
            self.price_range = (self.__price_min, self.default_max_price, self.default_price_increment)

        if not self.__price_min and self.__price_max:
            self.__price_max = int(self.__price_max)
            self.price_range = (0, self.__price_max, self.default_price_increment)
