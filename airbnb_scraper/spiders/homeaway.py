import base64
import http.client
import json
import logging
import scrapy


class HomeAwaySpider(scrapy.Spider):
    name = 'homeaway_spider'
    allowed_domains = ['homeaway.com']

    def __init__(self, clientId, clientSecret, *args, **kwargs):
        super(HomeAwaySpider, self).__init__(*args, **kwargs)

        self.start_urls = []

    def parse(self, response):
        """Determine number of pages in search results, and iterate through each page of results."""
        # ge the last page number on the page
        last_page_number = self._last_page_number_in_search(response)
        if last_page_number < 1:
            # abort the search if there are no results
            return
        else:
            # otherwise loop over all pages and scrape!
            page_urls = [response.url + "&page=" + str(pageNumber) for pageNumber in range(1, last_page_number + 1)]
            for page_url in page_urls:
                pass  # yield scrapy.Request(page_url, callback=self._parse_listing_results_page)

    @staticmethod
    def _last_page_number_in_search(response):
        """Get last page number of search results."""
        return 0
