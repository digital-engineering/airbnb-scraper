# -*- coding: utf-8 -*-
import json
import math
import random
import re
import scrapy

from deepbnb.items import DeepbnbItem
from urllib.parse import parse_qsl, urlparse


class BnbSpider(scrapy.Spider):
    name = 'bnb'
    allowed_domains = ['www.airbnb.com']
    data_cache = {}

    def start_requests(self):
        """Generate the first search request."""
        adults = 2
        checkin = '2020-01-15'
        checkout = '2020-02-15'
        client_session_id = random.choice([
            'a665bffd-a1fd-45c5-aa7b-de7d1ef1ba7b',
            '9b2aaa5d-ad0f-481c-b221-3accf65eee71',
            '66384df7-19fe-4e95-be1a-9c662e05001e'
        ])
        items_per_grid = 18
        key = 'd306zoyjsyarp7ifhu67rjxn52tv0t20'
        place_id = 'ChIJZYdwAomzxIARv1O7X3ZFbfQ'
        price_min = 0
        price_max = 2000
        query = 'Big%20Bear%20Lake%2C%20CA'
        urls = [('https://www.airbnb.com/api/v2/explore_tabs'
                 '?_format=for_explore_search_web'
                 '&adults={}'
                 '&auto_ib=true'
                 '&checkin={}'
                 '&checkout={}'
                 '&children=0'
                 '&client_session_id={}'
                 '&currency=USD'
                 '&current_tab_id=home_tab'
                 '&experiences_per_grid=20'
                 '&fetch_filters=true'
                 '&guidebooks_per_grid=20'
                 '&has_zero_guest_treatment=true'
                 '&hide_dates_and_guests_filters=false'
                 '&is_guided_search=true'
                 '&is_new_cards_experiment=true'
                 '&is_standard_search=true'
                 '&items_per_grid={}'
                 '&key={}'
                 '&locale=en'
                 '&metadata_only=false'
                 '&place_id={}'
                 '&price_min={}'
                 '&price_max={}'
                 '&query={}'
                 '&query_understanding_enabled=true'
                 '&refinement_paths%5B%5D=%2Fhomes'
                 '&room_types%5B%5D=Entire%20home%2Fapt'
                 '&satori_version=1.2.0'
                 '&screen_height=635'
                 '&screen_size=large'
                 '&screen_width=2040'
                 '&search_type=autocomplete_click'
                 '&selected_tab_id=home_tab'
                 '&show_groupings=true'
                 '&source=mc_search_bar'
                 '&supports_for_you_v3=true'
                 '&timezone_offset=-480'
                 '&version=1.6.5').format(
            adults,
            checkin,
            checkout,
            client_session_id,
            items_per_grid,
            key,
            place_id,
            price_min,
            price_max,
            query
        )]

        for url in urls:
            yield scrapy.Request(url, self._parse_search)

    def _parse_search(self, response):
        """Parse search response and generate URLs for all searches, then perform them."""
        items_per_grid = 18
        r = json.loads(response.body)
        explore_tabs = r['explore_tabs'][0]
        metadata = r['metadata']
        listings_count = explore_tabs['home_tab_metadata']['listings_count']
        federated_search_session_id = metadata['federated_search_session_id']
        query = metadata['query']
        s_tag = 'unSaHcwI'
        section_offset = 6
        has_next_page = explore_tabs['pagination_metadata']['has_next_page']
        last_search_session_id = explore_tabs['pagination_metadata'].get('search_session_id')
        qs_params = {k: v for k, v in parse_qsl(urlparse(response.url).query)}
        pages = math.ceil(listings_count / items_per_grid)
        search_urls = []
        for i in range(0, pages):
            items_offset = i * items_per_grid
            search_urls.append(('https://www.airbnb.com/api/v2/explore_tabs'
                                '?_format=for_explore_search_web'
                                '&adults={}'
                                '&auto_ib=true'
                                '&checkin={}'
                                '&checkout={}'
                                '&children=0'
                                '&client_session_id={}'
                                '&currency=USD'
                                '&current_tab_id=home_tab'
                                '&experiences_per_grid=20'
                                '&federated_search_session_id={}'
                                '&fetch_filters=true'
                                '&guidebooks_per_grid=20'
                                '&has_zero_guest_treatment=true'
                                '&hide_dates_and_guests_filters=false'
                                '&is_guided_search=true'
                                '&is_new_cards_experiment=true'
                                '&is_standard_search=true'
                                '&items_offset={}'
                                '&items_per_grid={}'
                                '&key={}'
                                '&last_search_session_id={}'
                                '&locale=en'
                                '&metadata_only=false'
                                '&place_id={}'
                                '&price_min={}'
                                '&price_max={}'
                                '&query={}'
                                '&query_understanding_enabled=true'
                                '&refinement_paths%5B%5D=%2Fhomes'
                                '&room_types%5B%5D=Entire%20home%2Fapt'
                                '&satori_version=1.2.0'
                                '&screen_height=635'
                                '&screen_size=large'
                                '&screen_width=2040'
                                '&search_type=pagination'
                                '&selected_tab_id=home_tab'
                                '&show_groupings=true'
                                '&source=mc_search_bar'
                                '&supports_for_you_v3=true'
                                '&timezone_offset=-480'
                                '&version=1.6.5').format(
                qs_params['adults'],
                qs_params['checkin'],
                qs_params['checkout'],
                qs_params['client_session_id'],
                federated_search_session_id,
                items_offset,
                items_per_grid,
                qs_params['key'],
                last_search_session_id,
                qs_params['place_id'],
                qs_params['price_min'],
                qs_params['price_max'],
                query
            ))

        for url in search_urls:
            yield scrapy.Request(url, callback=self._parse_listing_results_page)

    def _parse_listing_results_page(self, response):
        """Yield a separate request for each listing on the results page."""
        sections = json.loads(response.body).get('explore_tabs')[0].get('sections')
        ids = []
        for s in sections:
            if 'listings' not in s:
                continue

            for l in s['listings']:
                id = l['listing']['id']
                pricing = l['pricing_quote']
                self.data_cache[id] = {}
                self.data_cache[id]['monthly_price_factor'] = pricing['monthly_price_factor']
                self.data_cache[id]['weekly_price_factor'] = pricing['weekly_price_factor']
                self.data_cache[id]['total_price'] = pricing['price']['total']['amount']
                ids.append(id)

        qs_params = {k: v for k, v in parse_qsl(urlparse(response.url).query)}
        for i in ids:  # request each property page
            # 'https://www.airbnb.com/rooms/10707147?adults=2&check_in=2020-01-15&check_out=2020-02-15&source_impression_id=p3_1575867746_UbENcUB01H5K44VP'
            url = ('https://www.airbnb.com/rooms/{}'
                   '?adults={}'
                   '&check_in={}'
                   '&check_out={}'
                   ).format(i, qs_params['adults'], qs_params['checkin'], qs_params['checkout'])
            # request the url and pass the response to final listings parsing function
            # request.meta['search_price'] = int(matches[0].replace('$', '')) if len(matches) == 1 else None
            yield scrapy.Request(url, callback=self._parse_listing_contents)

    def _parse_listing_contents(self, response):
        """Obtain data from an individual listing page."""
        item = DeepbnbItem()
        xpath_match = response.xpath('//script[@id="data-state"]/text()').extract()[0]
        data = json.loads(xpath_match)

        listing = data['bootstrapData']['reduxData']['homePDP']['listingInfo']['listing']
        item['access'] = listing['sectioned_description']['access']

        item['additional_house_rules'] = listing['additional_house_rules']
        item['allows_events'] = listing['guest_controls']['allows_events']
        item['amenities'] = listing['listing_amenities']

        # bed_type = [di['value'] for di in listing['space_interface'] if di['label'] == 'Bed type']
        # if len(bed_type) > 0:
        #     item['bed_type'] = bed_type[0]

        if 'calendar_last_updated_at' in listing:
            item['calendar_updated_at'] = listing['calendar_last_updated_at']

        # item['cancel_policy'] = listing['cancellation_policy']
        item['city'] = listing['localized_city']

        # if listing['price_interface']['cleaning_fee']:
        #     item['cleaning_fee'] = listing['price_interface']['cleaning_fee']['value']

        item['description'] = listing['sectioned_description']['summary']
        item['host_id'] = listing['primary_host']['id']
        # item['house_rules'] = listing['house_rules']
        item['id'] = listing['id']

        if 'interaction' in listing['sectioned_description']:
            item['interaction'] = listing['sectioned_description']['interaction']

        if 'lat' in listing and 'lng' in listing:
            item['latitude'] = listing['lat']
            item['longitude'] = listing['lng']

        item['monthly_discount'] = self.data_cache[listing['id']]['monthly_price_factor']
        item['weekly_discount'] = self.data_cache[listing['id']]['weekly_price_factor']
        item['min_nights'] = listing['min_nights']
        item['total_price'] = self.data_cache[listing['id']]['total_price']
        item['name'] = '=HYPERLINK("{}", "{}")'.format(response.url, listing.get('name', response.url))
        item['neighborhood_overview'] = listing['sectioned_description']['neighborhood_overview']
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

        item['reviews'] = data['bootstrapData']['reduxData']['homePDP'].get('reviewsInfo', {}).get(
            'cumulativeReviews')

        item['room_type'] = listing['room_type_category']
        item['person_capacity'] = listing['p3_event_data_logging']['person_capacity']
        # item['price'] = listing['p3_event_data_logging']['price']
        item['satisfaction_guest'] = listing['p3_event_data_logging']['guest_satisfaction_overall']
        # item['search_price'] = response.meta['search_price']
        # item['space'] = listing['space_interface']
        # item['summary'] = listing['summary']
        item['url'] = response.url

        yield item
