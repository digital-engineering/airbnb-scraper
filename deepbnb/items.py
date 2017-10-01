# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class DeepbnbItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    access = scrapy.Field()
    additional_house_rules = scrapy.Field()
    allows_events = scrapy.Field()
    amenities = scrapy.Field()
    bed_type = scrapy.Field()
    calendar_updated_at = scrapy.Field()
    cancel_policy = scrapy.Field()
    city = scrapy.Field()
    cleaning_fee = scrapy.Field()
    description = scrapy.Field()
    host_id = scrapy.Field()
    house_rules = scrapy.Field()
    id = scrapy.Field()
    interaction = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()
    min_nights = scrapy.Field()
    monthly_discount = scrapy.Field()
    monthly_price = scrapy.Field()
    name = scrapy.Field()
    neighborhood_overview = scrapy.Field()
    nightly_price = scrapy.Field()
    notes = scrapy.Field()
    rating_accuracy = scrapy.Field()
    rating_checkin = scrapy.Field()
    rating_cleanliness = scrapy.Field()
    rating_communication = scrapy.Field()
    rating_location = scrapy.Field()
    rating_value = scrapy.Field()
    response_rate = scrapy.Field()
    response_time = scrapy.Field()
    review_count = scrapy.Field()
    review_score = scrapy.Field()
    reviews = scrapy.Field()
    room_type = scrapy.Field()
    person_capacity = scrapy.Field()
    price = scrapy.Field()
    satisfaction_guest = scrapy.Field()
    search_price = scrapy.Field()
    space = scrapy.Field()
    summary = scrapy.Field()
    url = scrapy.Field()
    weekly_discount = scrapy.Field()
