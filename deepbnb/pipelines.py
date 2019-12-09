# -*- coding: utf-8 -*-
import re
import webbrowser

from scrapy.exceptions import DropItem


class AirbnbScraperPipeline:

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            minimum_monthly_discount=crawler.settings.get('MINIMUM_MONTHLY_DISCOUNT'),
            minimum_weekly_discount=crawler.settings.get('MINIMUM_WEEKLY_DISCOUNT'),
            skip_list=crawler.settings.get('SKIP_LIST'),
            cannot_have=crawler.settings.get('CANNOT_HAVE'),
            must_have=crawler.settings.get('MUST_HAVE'),
            web_browser=crawler.settings.get('WEB_BROWSER')
        )

    def __init__(self, minimum_monthly_discount, minimum_weekly_discount, skip_list, cannot_have, must_have,
                 web_browser):
        """Class constructor."""
        self._fields_to_check = ['description', 'name', 'summary', 'reviews']
        self._minimum_monthly_discount = minimum_monthly_discount
        self._minimum_weekly_discount = minimum_weekly_discount

        self._skip_list = skip_list

        self._cannot_have_regex = cannot_have
        if self._cannot_have_regex:
            self._cannot_have_regex = re.compile(str(self._cannot_have_regex), re.IGNORECASE)

        self._must_have_regex = must_have
        if self._must_have_regex:
            self._must_have_regex = re.compile(str(self._must_have_regex), re.IGNORECASE)

        self._web_browser = web_browser
        if self._web_browser:
            self._web_browser += ' %s'  # append URL placeholder (%s)

    def process_item(self, item, spider):
        """Drop items not fitting parameters. Open in browser if specified. Return accepted items."""

        if self._skip_list and str(item['id']) in self._skip_list:
            raise DropItem('Item in skip list: {}'.format(item['id']))

        if self._minimum_monthly_discount and 'monthly_discount' in item:
            if item['monthly_discount'] < self._minimum_monthly_discount:
                raise DropItem('Monthly discount too low: {}'.format(item['monthly_discount']))

        if self._minimum_weekly_discount and 'weekly_discount' in item:
            if item['weekly_discount'] < self._minimum_monthly_discount:
                raise DropItem('Weekly discount too low: {}'.format(item['weekly_discount']))

        # check regexes
        if self._cannot_have_regex:
            for f in self._fields_to_check:
                v = str(item[f].encode('ASCII', 'replace'))
                if self._cannot_have_regex.search(v):
                    raise DropItem('Found: {}'.format(self._cannot_have_regex.pattern))

        if self._must_have_regex:
            has_must_haves = False
            for f in self._fields_to_check:
                v = str(item[f].encode('ASCII', 'replace'))
                if self._must_have_regex.search(v):
                    has_must_haves = True
                    break

            if not has_must_haves:
                raise DropItem('Not Found: {}'.format(self._must_have_regex.pattern))

        # open in browser
        if self._web_browser:
            webbrowser.get(self._web_browser).open(item['url'])

        return item
