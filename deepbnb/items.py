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
    amenity_ids = scrapy.Field()
    avg_rating = scrapy.Field()
    bathrooms = scrapy.Field()
    bedrooms = scrapy.Field()
    beds = scrapy.Field()
    business_travel_ready = scrapy.Field()
    city = scrapy.Field()
    country = scrapy.Field()
    description = scrapy.Field()
    host_id = scrapy.Field()
    house_rules = scrapy.Field()
    id = scrapy.Field()
    interaction = scrapy.Field()
    is_hotel = scrapy.Field()
    latitude = scrapy.Field()
    listing_expectations = scrapy.Field()
    longitude = scrapy.Field()
    max_nights = scrapy.Field()
    min_nights = scrapy.Field()
    monthly_price_factor = scrapy.Field()
    name = scrapy.Field()
    neighborhood_overview = scrapy.Field()
    # notes = scrapy.Field()
    person_capacity = scrapy.Field()
    photo_count = scrapy.Field()
    photos = scrapy.Field()
    place_id = scrapy.Field()
    price_rate = scrapy.Field()
    price_rate_type = scrapy.Field()
    province = scrapy.Field()
    rating_accuracy = scrapy.Field()
    rating_checkin = scrapy.Field()
    rating_cleanliness = scrapy.Field()
    rating_communication = scrapy.Field()
    rating_location = scrapy.Field()
    rating_value = scrapy.Field()
    review_count = scrapy.Field()
    room_and_property_type = scrapy.Field()
    room_type = scrapy.Field()
    room_type_category = scrapy.Field()
    satisfaction_guest = scrapy.Field()
    star_rating = scrapy.Field()
    state = scrapy.Field()
    total_price = scrapy.Field()
    transit = scrapy.Field()
    url = scrapy.Field()
    weekly_price_factor = scrapy.Field()
