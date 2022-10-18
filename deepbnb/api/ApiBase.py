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

    def _get_search_headers(self, response=None) -> dict:
        """Get headers for search requests."""
        headers = {
            'Accept':           '*/*',
            'Accept-Encoding':  'gzip,deflate',
            'Connection':       'keep-alive',
            'User-Agent':       'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
            'X-Airbnb-Api-Key': self._api_key
        }
        if response:
            headers['Cookie'] = str(response.headers.get('Set-Cookie'))

        return headers
