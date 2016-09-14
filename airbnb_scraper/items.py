# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class AirbnbScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    accuracy_rating = scrapy.Field()
    additional_house_rules = scrapy.Field()
    amenities = scrapy.Field()
    access = scrapy.Field()
    bed_type = scrapy.Field()
    calendar_updated_at = scrapy.Field()
    cancel_policy = scrapy.Field()
    description = scrapy.Field()
    host_id = scrapy.Field()
    hosting_id = scrapy.Field()
    house_rules = scrapy.Field()
    instant_book = scrapy.Field()
    interaction = scrapy.Field()
    min_nights = scrapy.Field()
    monthly_discount = scrapy.Field()
    name = scrapy.Field()
    neighborhood_overview = scrapy.Field()
    nightly_price = scrapy.Field()
    notes = scrapy.Field()
    rating_checkin = scrapy.Field()
    rating_cleanliness = scrapy.Field()
    rating_communication = scrapy.Field()
    response_rate = scrapy.Field()
    response_time = scrapy.Field()
    review_count = scrapy.Field()
    reviews = scrapy.Field()
    room_type = scrapy.Field()
    person_capacity = scrapy.Field()
    price = scrapy.Field()
    satisfaction_guest = scrapy.Field()
    space = scrapy.Field()
    summary = scrapy.Field()
    transit = scrapy.Field()
    url = scrapy.Field()
    weekly_discount = scrapy.Field()
