# -*- coding: utf-8 -*-
import logging
import json
import scrapy
import urllib.parse

from airbnb_scraper.items import AirbnbScraperItem


class AirbnbSpider(scrapy.Spider):
    name = "airbnb_spider"
    allowed_domains = ["airbnb.com"]

    def __init__(self, city, country, check_in, check_out, max_price, *args, **kwargs):
        super(AirbnbSpider, self).__init__(*args, **kwargs)
        url = 'https://www.airbnb.com/s/{}--{}'.format(city, country)
        url += '?checkin={}'.format(urllib.parse.quote(check_in))
        url += '&checkout={}'.format(urllib.parse.quote(check_out))
        url += '&price_max={}'.format(max_price)
        url += '&hosting_amenities%5B%5D=4&room_types%5B%5D=Entire+home%2Fapt'  # wifi, entire home
        self.start_urls = [url]

    def parse(self, response):
        # ge the last page number on the page
        last_page_number = self._last_page_number_in_search(response)
        if last_page_number < 1:
            # abort the search if there are no results
            return
        else:
            # otherwise loop over all pages and scrape!
            page_urls = [response.url + "&page=" + str(pageNumber) for pageNumber in range(1, last_page_number + 1)]
            for page_url in page_urls:
                yield scrapy.Request(page_url, callback=self.parse_listing_results_page)

    @staticmethod
    def _last_page_number_in_search(response):
        try:  # to get the last page number
            last_page_number = int(
                response.xpath('//ul[@class="list-unstyled"]/li[last()-1]/a/@href').extract()[0].split('page=')[1])
            return last_page_number

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
        item = AirbnbScraperItem()
        listing_array = response.xpath('//meta[@id="_bootstrap-listing"]/@content').extract()
        if listing_array:
            listing_json_all = json.loads(listing_array[0])
            listing_json = listing_json_all['listing']

            item['calendar_updated_at'] = listing_json['calendar_updated_at']
            item['min_nights'] = listing_json['min_nights']
            item['person_capacity'] = listing_json['person_capacity']
            item['reviews'] = '\n\n'.join([r['comments'] for r in listing_json['sorted_reviews']])

            listing_description = listing_json['localized_sectioned_description']
            if listing_description:
                item['access'] = listing_description['access']
                item['description'] = listing_description['description']
                item['house_rules'] = listing_description['house_rules']
                item['interaction'] = listing_description['interaction']
                item['name'] = listing_description['name']
                item['neighborhood_overview'] = listing_description['neighborhood_overview']
                item['notes'] = listing_description['notes']
                item['space'] = listing_description['space']
                item['summary'] = listing_description['summary']
                item['transit'] = listing_description['transit']
            else:
                item['name'] = listing_json['name']
                item['summary'] = listing_json['summary']
                item['description'] = listing_json['localized_description'] if listing_json[
                    'localized_description'] else listing_json['description']

        room_options_array = response.xpath('//meta[@id="_bootstrap-room_options"]/@content').extract()
        if room_options_array:
            room_options_json_all = json.loads(room_options_array[0])
            room_options_json = room_options_json_all['airEventData']
            item['rev_count'] = room_options_json['visible_review_count']
            item['amenities'] = room_options_json['amenities']
            item['host_id'] = room_options_json_all['hostId']
            item['hosting_id'] = room_options_json['hosting_id']
            item['room_type'] = room_options_json['room_type']
            item['price'] = room_options_json['price']
            item['bed_type'] = room_options_json['bed_type']
            item['person_capacity'] = room_options_json['person_capacity']
            item['cancel_policy'] = room_options_json['cancel_policy']
            item['rating_communication'] = room_options_json['communication_rating']
            item['rating_cleanliness'] = room_options_json['cleanliness_rating']
            item['rating_checkin'] = room_options_json['checkin_rating']
            item['satisfaction_guest'] = room_options_json['guest_satisfaction_overall']
            item['instant_book'] = room_options_json['instant_book_possible']
            item['accuracy_rating'] = room_options_json['accuracy_rating']
            item['response_time'] = room_options_json['response_time_shown']
            item['response_rate'] = room_options_json['reponse_rate_shown']
            item['nightly_price'] = room_options_json_all['nightly_price']

        item['url'] = response.url
        yield item

    def parse_listing_results_page(self, response):
        for href in response.xpath('//a[@class="media-photo media-cover"]/@href').extract():
            # get all href of the specified kind and join them to be a valid url
            url = response.urljoin(href)

            # request the url and pass the response to final listings parsing function
            yield scrapy.Request(url, callback=self._parse_listing_contents)
