import json

from abc import abstractmethod, ABC
from logging import LoggerAdapter
from urllib.parse import urlencode, urlunparse


class ApiBase(ABC):

    def __init__(self, api_key: str, logger: LoggerAdapter, currency: str):
        self._api_key = api_key
        self._currency = currency
        self._logger = logger

    @abstractmethod
    def api_request(self, **kwargs):
        raise NotImplementedError(f'{self.__class__.__name__}.api_request method is not defined')

    @staticmethod
    def build_airbnb_url(path, query=None):
        if query is not None:
            query = urlencode(query)

        return urlunparse(['https', 'www.airbnb.com', path, None, query, None])

    @property
    def api_key(self):
        return self._api_key

    @staticmethod
    def _put_json_param_strings(query: dict):
        """Property format JSON strings for 'variables' & 'extensions' params."""
        query['variables'] = json.dumps(query['variables'], separators=(',', ':'))
        query['extensions'] = json.dumps(query['extensions'], separators=(',', ':'))

    def read_data(self, response):
        """Read response data as json"""
        self._logger.debug(f"Parsing {response.url}")
        data = json.loads(response.body)

        return data

    def _get_search_headers(self) -> dict:
        """Get headers for search requests."""
        required_headers = {
            'Content-Type':              'application/json',
            'X-Airbnb-API-Key':          self._api_key,
            'X-Airbnb-GraphQL-Platform': 'web',
        }

        return required_headers | {
            # configurable parameters:
            'Device-Memory':                    '8',
            'DPR':                              '2.625',
            'ect':                              '4g',
            'Referer':                          'https://www.airbnb.com/',
            'User-Agent':                       'Mozilla/5.0 (Linux; Android 8.0; Pixel 2 Build/OPD3.170816.012) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Mobile Safari/537.36',
            'Viewport-Width':                   '1180',
            'X-Airbnb-GraphQL-Platform-Client': 'minimalist-niobe',
            'X-CSRF-Token':                     'V4$.airbnb.com$88klQ0-SkSk$f0wWUrY3M_I37iPj33S8w3-shUgkwi4Dq63e19JPlGQ=',
            'X-CSRF-Without-Token':             '1',
        }
