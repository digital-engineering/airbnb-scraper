import json
import requests
import scrapy

from urllib.parse import urlparse, parse_qs

from deepbnb.api.ApiBase import ApiBase


class PdpReviews(ApiBase):
    """Airbnb API v3 Reviews Endpoint"""

    def api_request(self, listing_id: str, limit: int = 7, start_offset: int = 0):
        """Perform API request."""
        # get first batch of reviews
        reviews, n_reviews_total = self._get_reviews_batch(listing_id, limit, start_offset)

        # get any additional batches
        start_idx = start_offset + limit
        for offset in range(start_idx, n_reviews_total, limit):
            r, _ = self._get_reviews_batch(listing_id, limit, offset)
            reviews.extend(r)

        return reviews

    def _get_reviews_batch(self, listing_id: str, limit: int, offset: int):
        """Get reviews for a given listing ID in batches."""
        url = self._get_url(listing_id, limit, offset)
        headers = self._get_search_headers()
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)
        pdp_reviews = data['data']['merlin']['pdpReviews']
        n_reviews_total = int(pdp_reviews['metadata']['reviewsCount'])
        reviews = [{
            'comments':   r['comments'],
            'created_at': r['createdAt'],
            'language':   r['language'],
            'rating':     r['rating'],
            'response':   r['response'],
        } for r in pdp_reviews['reviews']]

        return reviews, n_reviews_total

    def _get_url(self, listing_id: str, limit: int = 7, offset: int = None) -> str:
        _api_path = '/api/v3/PdpReviews'
        query = {
            'operationName': 'PdpReviews',
            'locale':        'en',
            'currency':      self._currency,
            'variables':     {
                'request': {
                    'fieldSelector':    'for_p3',
                    'limit':            limit,
                    'listingId':        listing_id,
                    'numberOfAdults':   '1',
                    'numberOfChildren': '0',
                    'numberOfInfants':  '0'
                }
            },
            'extensions':    {
                'persistedQuery': {
                    'version':    1,
                    'sha256Hash': '4730a25512c4955aa741389d8df80ff1e57e516c469d2b91952636baf6eee3bd'
                }
            }
        }

        if offset:
            query['variables']['request']['offset'] = offset

        self._put_json_param_strings(query)

        return self._build_airbnb_url(_api_path, query)

    def _parse_reviews(self, response):
        # parse qs
        parsed = urlparse(response.request.url)
        parsed_qs = parse_qs(parsed.query)
        variables = json.loads(parsed_qs['variables'][0])

        # extract data
        listing_id = variables['request']['listingId']
        limit = variables['request']['limit']
        offset = variables['request'].get('offset', 0)
        data = self.read_data(response)
        pdp_reviews = data['data']['merlin']['pdpReviews']
        n_reviews_total = int(pdp_reviews['metadata']['reviewsCount'])

        if offset == 0:  # get all other reviews
            for offset in range(limit, n_reviews_total, limit):
                url = self._get_url(listing_id, limit, offset)
                yield scrapy.Request(url, callback=self._parse_reviews, headers=self._get_search_headers())

        # return distilled review
        yield from ({
            'comments':   r['comments'],
            'created_at': r['createdAt'],
            'language':   r['language'],
            'rating':     r['rating'],
            'response':   r['response'],
        } for r in pdp_reviews['reviews'])
