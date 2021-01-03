from elasticsearch_dsl import Boolean, Document, Integer, Keyword, Text, GeoPoint, Float, Nested
from elasticsearch_dsl.connections import connections

connections.create_connection(hosts=['localhost'])


class Listing(Document):
    """Base class containing the common fields."""
    access = Text()
    additional_house_rules = Text()
    allows_events = Boolean()
    amenities = Keyword(multi=True)
    amenity_ids = Keyword(multi=True)
    avg_rating = Float()
    bathrooms = Float()
    bedrooms = Integer()
    beds = Integer()
    business_travel_ready = Boolean()
    city = Text(fields={'keyword': Keyword()}, required=True)
    country = Text(fields={'keyword': Keyword()}, required=True)
    coordinates = GeoPoint()
    description = Text()
    host_id = Integer(fields={'keyword': Keyword()})
    house_rules = Text()
    interaction = Text()
    is_hotel = Boolean()
    max_nights = Integer()
    min_nights = Integer()
    monthly_price_factor = Float()
    name = Text(fields={'keyword': Keyword()}, required=True)
    neighborhood_overview = Text()
    # notes = Text()
    person_capacity = Integer()
    photo_count = Integer()
    photos = Keyword(multi=True)
    place_id = Text(fields={'keyword': Keyword()})
    price_rate = Float()
    price_rate_type = Text(fields={'keyword': Keyword()}, required=True)
    province = Text(fields={'keyword': Keyword()})
    rating_accuracy = Float()
    rating_checkin = Float()
    rating_cleanliness = Float()
    rating_communication = Float()
    rating_location = Float()
    rating_value = Float()
    review_count = Integer()
    reviews = Nested()
    room_and_property_type = Text(fields={'keyword': Keyword()}, required=True)
    room_type = Text(fields={'keyword': Keyword()}, required=True)
    room_type_category = Text(fields={'keyword': Keyword()}, required=True)
    satisfaction_guest = Float()
    star_rating = Float()
    state = Text(fields={'keyword': Keyword()}, required=True)
    transit = Text()
    url = Text(fields={'keyword': Keyword()}, required=True)
    weekly_price_factor = Float()

    class Index:
        name = 'scrapy_airbnb_listing'

    def save(self, **kwargs):
        return super(Listing, self).save(**kwargs)


class ListingQuote(Document):
    listing_id = Integer()

    class Index:
        name = 'scrapy_airbnb_listing_quote'


def setup():
    # Create mapping in ElasticSearch - run this manually on setup
    Listing.init()
