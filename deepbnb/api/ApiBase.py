import json

from urllib.parse import urlencode, urlunparse


class ApiBase:

    def __init__(self, api_key, spider):
        self._api_key = api_key
        self._spider = spider

    @property
    def api_key(self):
        return self._api_key

    @staticmethod
    def _build_airbnb_url(path, query=None):
        if query is not None:
            query = urlencode(query)

        return urlunparse(['https', 'www.airbnb.com', path, None, query, None])

    @staticmethod
    def _fix_json_params(query):
        """Property format JSON strings for 'variables' & 'extensions' params."""
        query['variables'] = json.dumps(query['variables'], separators=(',', ':'))
        query['extensions'] = json.dumps(query['extensions'], separators=(',', ':'))

    def _get_search_headers(self):
        """Get headers for search requests."""
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
