import json
import scrapy
import re

from datetime import date, timedelta
from logging import LoggerAdapter
from scrapy import Spider
from urllib.parse import parse_qs, urlparse

from deepbnb.api.ApiBase import ApiBase


class ExploreSearch(ApiBase):
    """Airbnb API v3 Search Endpoint"""

    def __init__(
            self,
            api_key: str,
            logger: LoggerAdapter,
            currency: str,
            spider: Spider,
            room_types: list,
            geography: dict,
            query: str
    ):
        super().__init__(api_key, logger, currency)
        self.__geography = geography
        self.__room_types = room_types
        self.__query = query
        self.__spider = spider

    @staticmethod
    def add_search_params(params, response):
        parsed_qs = parse_qs(urlparse(response.request.url).query)
        variables = json.loads(parsed_qs['variables'][0])['request']
        if 'checkin' in variables:
            params['checkin'] = variables['checkin']
            params['checkout'] = variables['checkout']

        if 'priceMax' in variables:
            params['priceMax'] = variables['priceMax']

        if 'priceMin' in variables:
            params['priceMin'] = variables['priceMin']

        if 'ne_lat' in parsed_qs:
            params['ne_lat'] = parsed_qs['ne_lat'][0]

        if 'ne_lng' in parsed_qs:
            params['ne_lng'] = parsed_qs['ne_lng'][0]

        if 'sw_lat' in parsed_qs:
            params['sw_lat'] = parsed_qs['sw_lat'][0]

        if 'sw_lng' in parsed_qs:
            params['sw_lng'] = parsed_qs['sw_lng'][0]

    def api_request(self, query, params=None, callback=None, response=None, headers=None):
        """Perform API request."""
        request = response.follow if response else scrapy.Request
        callback = callback or self.__spider.parse
        url = self._get_url(query, params)
        search_headers = self._get_search_headers(response)
        headers = headers | search_headers if headers else search_headers
        return request(url, callback, headers=headers, meta={'playwright': True}, cb_kwargs={'headers': headers})

    def get_paginated_search_params(self, response, data):
        """Consolidate search parameters and return result."""
        metadata = data['data']['dora']['exploreV3']['metadata']
        pagination = metadata['paginationMetadata']
        filter_state = data['data']['dora']['exploreV3']['filters']['state']

        place_id = self.__geography.get('place_id', metadata['geography']['placeId'])
        query = [fs['value']['stringValue'] for fs in filter_state if fs['key'] == 'query'][0]

        params = {'placeId': place_id, 'query': query}
        if pagination['hasNextPage']:
            params['lastSearchSessionId'] = pagination['searchSessionId']

        self.add_search_params(params, response)

        return params

    def parse_landing_page(self, response):
        """Parse search response and generate URLs for all searches, then perform them."""
        self._logger.debug(f"Parsing {response.url}")
        json_response = response.xpath('body/pre/text()').get()  # remove html wrapper
        data = json.loads(json_response)
        search_params = self.get_paginated_search_params(response, data)

        self.__geography.update(data['data']['dora']['exploreV3']['metadata']['geography'])
        self._logger.info(f"Geography:\n{self.__geography}")

        yield self.api_request(self.__query, search_params, self.__spider.parse, response)

    def perform_checkin_start_requests(
            self,
            checkin: str,
            checkout: str,
            checkin_range_spec: str,
            checkout_range_spec: str,
            params: dict
    ):
        """Perform requests for start URLs.

        :param checkin:
        :param checkout:
        :param checkin_range_spec:
        :param checkout_range_spec:
        :param params:
        :return:
        """
        # single request for static start and end dates
        if not (checkin_range_spec or checkout_range_spec):  # simple start and end date
            params['checkin'] = checkin
            params['checkout'] = checkout
            yield self.api_request(self.__query, params, self.parse_landing_page)

        # multi request for dynamic start and static end date
        if checkin_range_spec and not checkout_range_spec:  # ranged start date, single end date, iterate over checkin range
            checkin_start_date, checkin_range = self._build_date_range(checkin, checkin_range_spec)
            for i in range(checkin_range.days + 1):  # + 1 to include end date
                params['checkin'] = str(checkin_start_date + timedelta(days=i))
                params['checkout'] = checkout
                yield self.api_request(self.__query, params, self.parse_landing_page)

        # multi request for static start and dynamic end date
        if checkout_range_spec and not checkin_range_spec:  # ranged end date, single start date, iterate over checkout range
            checkout_start_date, checkout_range = self._build_date_range(checkout, checkout_range_spec)
            for i in range(checkout_range.days + 1):  # + 1 to include end date
                params['checkout'] = str(checkout_start_date + timedelta(days=i))
                params['checkin'] = checkin
                yield self.api_request(self.__query, params, self.parse_landing_page)

        # double nested multi request, iterate over both start and end date ranges
        if checkout_range_spec and checkin_range_spec:
            checkin_start_date, checkin_range = self._build_date_range(checkin, checkin_range_spec)
            checkout_start_date, checkout_range = self._build_date_range(checkout, checkout_range_spec)
            for i in range(checkin_range.days + 1):  # + 1 to include end date
                params['checkin'] = str(checkin_start_date + timedelta(days=i))
                for j in range(checkout_range.days + 1):  # + 1 to include end date
                    params['checkout'] = str(checkout_start_date + timedelta(days=j))
                    yield self.api_request(self.__query, params, self.parse_landing_page)

    @staticmethod
    def _build_date_range(iso_date: str, range_spec: str):
        """Calculate start and end dates for a range. Return start date and timedelta for number of days."""
        base_date = date.fromisoformat(iso_date)
        if range_spec.startswith('+-'):  # +-7
            days = float(re.match(r'\+-(\d+)', range_spec).group(1))
            start_date = base_date - timedelta(days=days)
            end_date = base_date + timedelta(days=days)
        else:  # +0-3
            result = re.match(r'\+(\d+)-(\d+)', range_spec)
            post_days = float(result.group(1))
            pre_days = float(result.group(2))
            start_date = base_date - timedelta(days=pre_days)
            end_date = base_date + timedelta(days=post_days)

        return start_date, end_date - start_date

    def _get_url(self, search_string: str, params: dict = None):
        _api_path = '/api/v3/ExploreSearch'
        query = {
            'operationName': 'ExploreSearch',
            'locale':        'en',
            'currency':      self._currency,
            '_cb':           'ld7rar1fhh6if',
        }
        data = {
            'variables':  {
                'request': {
                    'metadataOnly':          False,
                    'version':               '1.7.9',
                    'itemsPerGrid':          20,
                    'tabId':                 'home_tab',
                    'refinementPaths':       ['/homes'],
                    'source':                'structured_search_input_header',
                    'searchType':            'filter_change',
                    'query':                 search_string,
                    # 'roomTypes':             self.__room_types,
                    'cdnCacheSafe':          False,
                    'simpleSearchTreatment': 'simple_search_only',
                    'treatmentFlags':        [
                        'simple_search_1_1',
                        'simple_search_desktop_v3_full_bleed',
                        'flexible_dates_options_extend_one_three_seven_days'
                    ],
                    'screenSize':            'large'
                }
            },
            'extensions': {
                'persistedQuery': {
                    'version':    1,
                    'sha256Hash': '13aa9971e70fbf5ab888f2a851c765ea098d8ae68c81e1f4ce06e2046d91b6ea'
                }
            }
        }
        if params:
            data['variables']['request'] |= params

        self._put_json_param_strings(data)

        url = self.build_airbnb_url(_api_path, query)
        url += '&variables=%s' % data['variables']
        url += '&extensions=%s' % data['extensions']

        return url
