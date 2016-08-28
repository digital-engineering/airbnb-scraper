# -*- coding: utf-8 -*-
import re

from scrapy.exceptions import DropItem


class AirbnbScraperPipeline:
    def __init__(self):
        self._condition_regex = re.compile(r'(balcon|terra|patio)', re.IGNORECASE)
        self._fields_to_check = ['description', 'name', 'summary', 'reviews']

    def process_item(self, item, spider):
        for f in self._fields_to_check:
            v = str(item[f])
            if self._condition_regex.search(v):
                return item

        raise DropItem('No terrace or patio!')
