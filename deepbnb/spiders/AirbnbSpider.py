# -*- coding: utf-8 -*-
import logging
import json
import re
import scrapy

from deepbnb.items import DeepbnbItem
from scrapy.utils.response import open_in_browser
from scrapy_splash.request import SplashRequest


class AirbnbSpider(scrapy.Spider):
    name = "airbnb"
    allowed_domains = ["airbnb.com"]

    _query_parts = {
        'adults': 1,
        'check_in': '2017-10-27',
        'check_out': '2017-11-30',
        'guests': 1,
        'hosting_amenities': {
            # Desired hosting amenities and corresponding IDs. Determined by observing search GET parameters.
            'a/c': 5,
            'kitchen': 8,
            'tv': 58,
            'washer': 33,
            'dryer': 34,
            'wifi': 4,
        },
        'map': {
            'coords': {
                'ne_lat': 33.339050291964746,
                'ne_lng': -117.04326732747506,
                'sw_lat': 32.561755675390934,
                'sw_lng': -117.69970043294381
            },
            'zoom': 10
        },
        'neighborhoods': None,
        'pets': 'false',
        'price_max': 2750,
        'price_min': None,
        'query': 'California--United-States',
        'refinements': ['homes'],
        'room_types': ['Entire%20home%2Fapt'],
        'search_by_map': 'true'
    }

    def start_requests(self):
        urls = [self._build_airbnb_start_url()]
        for url in urls:
            yield SplashRequest(url, self.parse, args={'wait': 5})

    def parse(self, response):
        """Determine number of pages in search results, and iterate through each page of results."""
        # get the last page number on the page
        last_page_number = self._last_page_number_in_search(response)
        if last_page_number < 1:
            # abort the search if there are no results
            return
        # otherwise loop over all pages and scrape!
        page_urls = [response.url + "&section_offset=" + str(pageNumber) for pageNumber in range(0, last_page_number)]
        for page_url in page_urls:
            yield SplashRequest(page_url, self._parse_listing_results_page, args={'wait': 5})

    def _build_airbnb_start_url(self):
        """Generate the search URL from given parameters.

        Example URL:
        https://www.airbnb.com/s/California--United-States/homes
                                ?checkin=2017-10-14&checkout=2017-11-18&guests=1&adults=1&pets=false
                                &refinements%5B%5D=homes&room_types%5B%5D=Entire%20home%2Fapt
        """
        url = 'https://www.airbnb.com/s/{}/homes'.format(self._query_parts['query'])
        query_parts = []
        if self._query_parts['check_in'] and self._query_parts['check_out']:
            query_parts.append(
                'checkin={}&checkout={}'.format(self._query_parts['check_in'], self._query_parts['check_out']))

        if self._query_parts['price_max']:
            query_parts.append('price_max={}'.format(self._query_parts['price_max']))

        if self._query_parts['price_min']:
            query_parts.append('price_min={}'.format(self._query_parts['price_min']))

        if self._query_parts['hosting_amenities']:
            amenities = self._query_parts['hosting_amenities'].values()
            for a in amenities:
                query_parts.append('&hosting_amenities%5B%5D={}'.format(a))

        if self._query_parts['neighborhoods']:
            neighborhoods = map(lambda x: x.strip().replace(' ', '+'), self._query_parts['neighborhoods'].split(','))
            for n in neighborhoods:
                query_parts.append('&neighborhoods%5B%5D={}'.format(n))

        if self._query_parts['adults']:
            query_parts.append('adults={}'.format(self._query_parts['adults']))

        if self._query_parts['guests']:
            query_parts.append('guests={}'.format(self._query_parts['guests']))

        if self._query_parts['pets']:
            query_parts.append('pets={}'.format(self._query_parts['pets']))

        if self._query_parts['refinements']:
            for r in self._query_parts['refinements']:
                query_parts.append('refinements%5B%5D={}'.format(r))

        if self._query_parts['room_types']:
            for r in self._query_parts['room_types']:
                query_parts.append('room_types%5B%5D={}'.format(r))

        if self._query_parts['search_by_map']:
            for name, value in self._query_parts['map']['coords'].items():
                query_parts.append('{}={}'.format(name, value))
            query_parts.append('zoom={}'.format(self._query_parts['map']['zoom']))

        url += '?{}'.format('&'.join(query_parts))

        return url

    @staticmethod
    def _last_page_number_in_search(response):
        """Get last page number of search results."""
        try:  # to get the last page number
            last_page = response.xpath('//ul[@data-id="SearchResultsPagination"]/li[last()-1]/a/div/text()').extract()
            return int(last_page[0])
        except IndexError:  # if there is no page number
            # get the reason from the page
            reason = response.xpath('//p[@class="text-lead"]/text()').extract()
            # and if it contains the key words set last page equal to 0
            if reason and ('find any results that matched your criteria' in reason[0]):
                logging.log(logging.DEBUG, 'No results on page' + response.url)
                return 0
            else:
                # otherwise we can conclude that the page
                # has results but that there is only one page.
                return 1

    @staticmethod
    def _parse_listing_contents(response):
        """Obtain data from an individual listing page."""
        item = DeepbnbItem()
        xpath_match = response.xpath('//script[starts-with(@data-hypernova-key,"p3show_")]/text()').extract()[0]
        data = json.loads(xpath_match[4:len(xpath_match) - 3])  # remove leading <!-- and ending -->

        listing = data['bootstrapData']['reduxData']['marketplacePdp']['listingInfo']['listing']
        item['access'] = listing['sectioned_description']['access']

        item['additional_house_rules'] = listing['additional_house_rules']
        item['allows_events'] = listing['guest_controls']['allows_events']
        item['amenities'] = listing['listing_amenities']

        bed_type = [di['value'] for di in listing['space_interface'] if di['label'] == 'Bed type']
        if len(bed_type) > 0:
            item['bed_type'] = bed_type[0]

        if 'calendar_last_updated_at' in listing:
            item['calendar_updated_at'] = listing['calendar_last_updated_at']

        item['cancel_policy'] = listing['cancellation_policy']
        item['city'] = listing['city']

        if listing['price_interface']['cleaning_fee']:
            item['cleaning_fee'] = listing['price_interface']['cleaning_fee']['value']

        item['description'] = listing['description']
        item['host_id'] = listing['primary_host']['id']
        item['house_rules'] = listing['house_rules']
        item['id'] = listing['id']

        if 'interaction' in listing['sectioned_description']:
            item['interaction'] = listing['sectioned_description']['interaction']

        if 'lat' in listing and 'lng' in listing:
            item['latitude'] = listing['lat']
            item['longitude'] = listing['lng']

        item['monthly_discount'] = listing.get('price_interface', {}).get('monthly_discount', {}).get('value')
        item['min_nights'] = listing['min_nights']
        price = response.xpath('//span[@id="book-it-price-string"]//text()').extract()
        if len(price) == 0:
            print("Can't get price value for response: {}".format(price))
            price_value = 0
        else:
            price_value = int(price[0].replace('$', ''))
        item['monthly_price'] = price_value if (1 in price and price[1] == 'per month') else None
        item['name'] = '=HYPERLINK("{}", "{}")'.format(response.url, listing.get('name', response.url))
        item['neighborhood_overview'] = listing['sectioned_description']['neighborhood_overview']
        item['nightly_price'] = price_value if (1 in price and price[1] == 'per night') else None
        item['notes'] = listing['sectioned_description']['notes']

        item['rating_accuracy'] = listing['p3_event_data_logging']['accuracy_rating']
        item['rating_checkin'] = listing['p3_event_data_logging']['checkin_rating']
        item['rating_cleanliness'] = listing['p3_event_data_logging']['cleanliness_rating']
        item['rating_communication'] = listing['p3_event_data_logging']['communication_rating']
        item['rating_location'] = listing['p3_event_data_logging']['location_rating']
        item['rating_value'] = listing['p3_event_data_logging']['value_rating']
        item['response_rate'] = listing['p3_event_data_logging']['response_rate_shown']
        item['response_time'] = listing['p3_event_data_logging']['response_time_shown']

        item['review_count'] = listing['review_details_interface']['review_count']
        item['review_score'] = listing['review_details_interface']['review_score']

        item['reviews'] = data['bootstrapData']['reduxData']['marketplacePdp'].get('reviewsInfo', {}).get(
            'cumulativeReviews')

        item['room_type'] = listing['room_type_category']
        item['person_capacity'] = listing['p3_event_data_logging']['person_capacity']
        item['price'] = listing['p3_event_data_logging']['price']
        item['satisfaction_guest'] = listing['p3_event_data_logging']['guest_satisfaction_overall']
        item['search_price'] = response.meta['search_price']
        item['space'] = listing['space_interface']
        item['summary'] = listing['summary']
        item['url'] = response.url
        if 'price_interface' in listing and 'weekly_discount' in listing['price_interface']:
            item['weekly_discount'] = listing['price_interface']['weekly_discount'].get('value')

        yield item

    def _parse_listing_results_page(self, response):
        """Yield a separate request for each listing on the results page."""
        links = response.xpath('//a[starts-with(@target, "listing") and @rel="noopener"]')
        for link in links:
            # get all href of the specified kind and join them to be a valid url
            href = link.xpath('@href').extract()
            url = response.urljoin(href[0])
            text_nodes = link.xpath('.//text()').extract()
            matches = list(filter(lambda x: re.match(r'\$[\d,]+', x), text_nodes))
            # request the url and pass the response to final listings parsing function
            request = SplashRequest(url, self._parse_listing_contents, args={'wait': 15})
            request.meta['search_price'] = int(matches[0].replace('$', '')) if len(matches) == 1 else None
            yield request
