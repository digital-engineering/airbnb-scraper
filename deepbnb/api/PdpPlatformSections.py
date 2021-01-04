import lxml.html
import re
import scrapy

from typing import Union
from logging import LoggerAdapter

from deepbnb.api.ApiBase import ApiBase
from deepbnb.api.PdpReviews import PdpReviews
from deepbnb.items import DeepbnbItem


class PdpPlatformSections(ApiBase):
    """Airbnb API v3 Property Display Endpoint"""

    # Unused. This is just a list of sections where we presently pull data from. (@see `parse_listing_contents()`)
    SECTION_IDS = [
        'AMENITIES_DEFAULT',
        'DESCRIPTION_DEFAULT',
        'HOST_PROFILE_DEFAULT',
        'LOCATION_DEFAULT',
        'POLICIES_DEFAULT',
    ]

    def __init__(
            self,
            api_key: str,
            logger: LoggerAdapter,
            currency: str,
            data_cache: dict,
            geography: dict,
            pdp_reviews: PdpReviews
    ):
        super().__init__(api_key, logger, currency)
        self.__data_cache = data_cache
        self.__geography = geography
        self.__regex_amenity_id = re.compile(r'^([a-z0-9]+_)+([0-9]+)_')
        self.__pdp_reviews = pdp_reviews

    def api_request(self, listing_id: str):
        """Generate scrapy.Request for listing page."""
        _api_path = '/api/v3/PdpPlatformSections'
        query = {
            'operationName': 'PdpPlatformSections',
            'locale':        'en',
            'currency':      self._currency,
            'variables':     {
                'request': {
                    'id':                            listing_id,
                    'layouts':                       ['SIDEBAR', 'SINGLE_COLUMN'],
                    'pdpTypeOverride':               None,
                    'translateUgc':                  None,
                    'preview':                       False,
                    'bypassTargetings':              False,
                    'displayExtensions':             None,
                    'adults':                        '1',
                    'children':                      None,
                    'infants':                       None,
                    'causeId':                       None,
                    'disasterId':                    None,
                    'priceDropSource':               None,
                    'promotionUuid':                 None,
                    'selectedCancellationPolicyId':  None,
                    'forceBoostPriorityMessageType': None,
                    'privateBooking':                False,
                    'invitationClaimed':             False,
                    'discountedGuestFeeVersion':     None,
                    'staysBookingMigrationEnabled':  False,
                    'useNewSectionWrapperApi':       False,
                    'previousStateCheckIn':          None,
                    'previousStateCheckOut':         None,
                    'federatedSearchId':             None,
                    'interactionType':               None,
                    'searchId':                      None,
                    'sectionIds':                    None,
                    'checkIn':                       None,
                    'checkOut':                      None,
                    'p3ImpressionId':                'p3_1608841700_z2VzPeybmBEdZG20'
                }
            },
            'extensions':    {
                'persistedQuery': {
                    'version':    1,
                    'sha256Hash': '625a4ba56ba72f8e8585d60078eb95ea0030428cac8772fde09de073da1bcdd0'
                }
            }
        }

        self._put_json_param_strings(query)
        url = self._build_airbnb_url(_api_path, query)

        return scrapy.Request(url, callback=self.parse_listing_contents, headers=self._get_search_headers())

    def parse_listing_contents(self, response):
        """Obtain data from an individual listing page, combine with cached data, and return DeepbnbItem."""
        # Collect base data
        data = self.read_data(response)
        pdp_sections = data['data']['merlin']['pdpSections']
        listing_id = pdp_sections['id']
        sections = pdp_sections['sections']
        metadata = pdp_sections['metadata']
        logging_data = metadata['loggingContext']['eventDataLogging']

        # Get sections
        amenities_section = [s for s in sections if s['sectionId'] == 'AMENITIES_DEFAULT'][0]['section']
        description_section = [s for s in sections if s['sectionId'] == 'DESCRIPTION_DEFAULT'][0]['section']
        host_profile = [s for s in sections if s['sectionId'] == 'HOST_PROFILE_DEFAULT'][0]['section']
        location = [s for s in sections if s['sectionId'] == 'LOCATION_DEFAULT'][0]['section']
        policies = [s for s in sections if s['sectionId'] == 'POLICIES_DEFAULT'][0]['section']

        # Collect amenity data
        amenities_groups = amenities_section['seeAllAmenitiesGroups']
        amenities_access = [g['amenities'] for g in amenities_groups if g['title'] == 'Guest access']
        amenities_avail = [amenity for g in amenities_groups for amenity in g['amenities'] if amenity['available']]

        # Structure data
        listing_data_cached = self.__data_cache[listing_id]
        item = DeepbnbItem(
            id=listing_id,
            access=self._render_titles(amenities_access[0]) if amenities_access else None,
            additional_house_rules=policies['additionalHouseRules'],
            allows_events='No parties or events' in [r['title'] for r in policies['houseRules']],
            amenities=self._render_titles(amenities_avail, sep=' - ', join=False),
            amenity_ids=list(self._get_amenity_ids(amenities_avail)),
            avg_rating=listing_data_cached['avg_rating'],
            bathrooms=listing_data_cached['bathrooms'],
            bedrooms=listing_data_cached['bedrooms'],
            beds=listing_data_cached['beds'],
            business_travel_ready=listing_data_cached['business_travel_ready'],
            city=listing_data_cached.get('city', self.__geography['city']),
            country=self.__geography['country'],
            description=self._html_to_text(description_section['htmlDescription']['htmlText']),
            host_id=listing_data_cached['host_id'],
            house_rules=[r['title'] for r in policies['houseRules']],
            is_hotel=metadata['bookingPrefetchData']['isHotelRatePlanEnabled'],
            latitude=listing_data_cached['latitude'],
            listing_expectations=self._render_titles(policies['listingExpectations']) if policies else None,
            longitude=listing_data_cached['longitude'],
            # max_nights=listing.get('max_nights'),
            # min_nights=listing['min_nights'],
            monthly_price_factor=listing_data_cached['monthly_price_factor'],
            name=listing_data_cached.get('name', listing_id),
            neighborhood_overview=listing_data_cached.get('neighborhood_overview'),
            # notes=listing['sectioned_description']['notes'],
            person_capacity=listing_data_cached['person_capacity'],
            photo_count=listing_data_cached['photo_count'],
            photos=listing_data_cached['photos'],
            place_id=self.__geography['placeId'],
            price_rate=listing_data_cached['price_rate'],
            price_rate_type=listing_data_cached['price_rate_type'],
            province=self.__geography.get('province'),
            rating_accuracy=logging_data['accuracyRating'],
            rating_checkin=logging_data['checkinRating'],
            rating_cleanliness=logging_data['cleanlinessRating'],
            rating_communication=logging_data['communicationRating'],
            rating_location=logging_data['locationRating'],
            rating_value=logging_data['valueRating'],
            review_count=listing_data_cached['review_count'],
            reviews=self.__pdp_reviews.api_request(listing_id, 50),
            room_and_property_type=listing_data_cached['room_and_property_type'],
            room_type=listing_data_cached['room_type'],
            room_type_category=listing_data_cached['room_type_category'],
            satisfaction_guest=logging_data['guestSatisfactionOverall'],
            star_rating=listing_data_cached['star_rating'],
            state=self.__geography['state'],
            # summary=listing['sectioned_description']['summary'],
            total_price=listing_data_cached['total_price'],
            url="https://www.airbnb.com/rooms/{}".format(listing_id),
            weekly_price_factor=listing_data_cached['weekly_price_factor']
        )

        self._get_detail_property(item, 'transit', 'Getting around', location['seeAllLocationDetails'], 'content')
        self._get_detail_property(item, 'interaction', 'During your stay', host_profile['hostInfos'], 'html')

        return item

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Get plaintext from HTML."""
        return lxml.html.document_fromstring(html).text_content()

    @staticmethod
    def _render_titles(title_list: list, sep: str = ': ', join=True) -> Union[str, list]:
        """Render list of objects with titles and subtitles into string."""
        lines = []
        for t in title_list:
            line = '{}{}{}'.format(t['title'], sep, t['subtitle']) if t.get('subtitle') else t.get('title')
            lines.append(line)

        return '\n'.join(lines) if join else lines

    def _get_amenity_ids(self, amenities: list):
        """Extract amenity id from `id` string field."""
        for amenity in amenities:
            match = self.__regex_amenity_id.match(amenity['id'])
            yield int(match.group(match.lastindex))

    def _get_detail_property(self, item, prop, title, prop_list, key):
        """Search for matching title in property list for prop. If exists, add htmlText for key to item."""
        if title in [i['title'] for i in prop_list]:
            item[prop] = self._html_to_text([i[key]['htmlText'] for i in prop_list if i['title'] == title][0])
