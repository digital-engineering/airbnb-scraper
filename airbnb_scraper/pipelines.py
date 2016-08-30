# -*- coding: utf-8 -*-
import re
import webbrowser

from scrapy.conf import settings
from scrapy.exceptions import DropItem


class AirbnbScraperPipeline:
    def __init__(self):
        """Class constructor."""
        self._cannot_have_regex = settings.get('CANNOT_HAVE', None)
        if self._cannot_have_regex:
            self._cannot_have_regex = re.compile(str(self._cannot_have_regex), re.IGNORECASE)

        self._web_browser = settings.get('WEB_BROWSER', None)
        if self._web_browser:
            self._web_browser += ' %s'  # append URL placeholder

        self._must_have_regex = settings.get('MUST_HAVE', None)
        if self._must_have_regex:
            self._must_have_regex = re.compile(str(self._must_have_regex), re.IGNORECASE)

        self._fields_to_check = ['description', 'name', 'summary', 'reviews']

    def process_item(self, item, spider):
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

        if self._web_browser:
            webbrowser.get(self._web_browser).open(item['url'])

        return item
