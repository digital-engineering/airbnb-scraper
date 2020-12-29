# -*- coding: utf-8 -*-
import scrapy
import re

from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

from deepbnb.api.ApiBase import ApiBase


class ExploreSearch(ApiBase):
    """Class to interact with the Airbnb ExploreSearch API"""

    @staticmethod
    def add_search_params(params, response):
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

    def api_request(self, place, params=None, response=None, callback=None):
        """Perform API request."""
        request = response.follow if response else scrapy.Request
        callback = callback or self._spider.parse
        url = self.get_search_api_url(place, params)
        headers = self._get_search_headers()

        return request(url, callback, headers=headers)

    def get_paginated_search_params(self, response, data):
        """Consolidate search parameters and return result."""
        metadata = data['data']['dora']['exploreV3']['metadata']
        pagination = metadata['paginationMetadata']
        filter_state = data['data']['dora']['exploreV3']['filters']['state']
        place_id = self._spider._geography.get('place_id', metadata['geography']['placeId'])
        query = [fs['value']['stringValue'] for fs in filter_state if fs['key'] == 'query'][0]
        params = {
            'searchSessionId': pagination['searchSessionId'],
            'place_id':        place_id,
            'query':           query
        }

        # if pagination['hasNextPage']:
        #     params['last_search_session_id'] = pagination['searchSessionId']

        self.add_search_params(params, response)

        return params

    def get_search_api_url(self, place, params=None):
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
                    "query":                 place,
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

        # if self.settings.get('PROPERTY_AMENITIES'):
        #     amenities = self.settings.get('PROPERTY_AMENITIES').values()
        #     query = list(query.items())  # convert dict to list of tuples because we need multiple identical keys
        #     for a in amenities:
        #         query.append(('amenities[]', a))

        self._fix_json_params(query)
        url = self._build_airbnb_url(_api_path, query)

        return url

    def perform_checkin_start_requests(self, checkin_range_spec: str, checkout_range_spec: str, params: dict):
        """Perform requests for start URLs.

        :param checkin_range_spec:
        :param checkout_range_spec:
        :param params:
        :return:
        """
        # single request for static start and end dates
        if not (checkin_range_spec or checkout_range_spec):  # simple start and end date
            params['checkin'] = self._spider._checkin
            params['checkout'] = self._spider._checkout
            yield self.api_request(params, callback=self._spider.parse_landing_page)

        # multi request for dynamic start and static end date
        if checkin_range_spec and not checkout_range_spec:  # ranged start date, single end date, iterate over checkin range
            checkin_start_date, checkin_range = self._build_date_range(self._spider._checkin, checkin_range_spec)
            for i in range(checkin_range.days + 1):  # + 1 to include end date
                params['checkin'] = self._spider._checkin = str(checkin_start_date + timedelta(days=i))
                params['checkout'] = self._spider._checkout
                yield self.api_request(params, callback=self._spider.parse_landing_page)

        # multi request for static start and dynamic end date
        if checkout_range_spec and not checkin_range_spec:  # ranged end date, single start date, iterate over checkout range
            checkout_start_date, checkout_range = self._build_date_range(self._spider._checkout, checkout_range_spec)
            for i in range(checkout_range.days + 1):  # + 1 to include end date
                params['checkout'] = self._spider._checkout = str(checkout_start_date + timedelta(days=i))
                params['checkin'] = self._spider._checkin
                yield self.api_request(params, callback=self._spider.parse_landing_page)

        # double nested multi request, iterate over both start and end date ranges
        if checkout_range_spec and checkin_range_spec:
            checkin_start_date, checkin_range = self._build_date_range(self._spider._checkin, checkin_range_spec)
            checkout_start_date, checkout_range = self._build_date_range(self._spider._checkout, checkout_range_spec)
            for i in range(checkin_range.days + 1):  # + 1 to include end date
                params['checkin'] = self._spider._checkin = str(checkin_start_date + timedelta(days=i))
                for j in range(checkout_range.days + 1):  # + 1 to include end date
                    params['checkout'] = self._spider._checkout = str(checkout_start_date + timedelta(days=j))
                    yield self.api_request(params, callback=self._spider.parse_landing_page)

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

