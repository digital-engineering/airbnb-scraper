import scrapy

from deepbnb.api.ApiBase import ApiBase


class PdpPlatformSections(ApiBase):

    def listing_api_request(self, listing: dict):
        """Generate scrapy.Request for listing page."""
        _api_path = '/api/v3/PdpPlatformSections'
        # https://www.airbnb.com/api/v3/PdpPlatformSections
        # ?operationName=PdpPlatformSections
        # &locale=en
        # &currency=USD
        # &variables={"request":{"id":"38052139","layouts":["SIDEBAR","SINGLE_COLUMN"],"pdpTypeOverride":null,"translateUgc":null,"preview":false,"bypassTargetings":false,"displayExtensions":null,"adults":"1","children":null,"infants":null,"causeId":null,"disasterId":null,"priceDropSource":null,"promotionUuid":null,"selectedCancellationPolicyId":null,"forceBoostPriorityMessageType":null,"privateBooking":false,"invitationClaimed":false,"discountedGuestFeeVersion":null,"staysBookingMigrationEnabled":false,"useNewSectionWrapperApi":false,"previousStateCheckIn":null,"previousStateCheckOut":null,"federatedSearchId":null,"interactionType":null,"searchId":null,"sectionIds":["EDUCATION_FOOTER_BANNER_MODAL","BOOK_IT_CALENDAR_SHEET","BOOK_IT_CALENDAR_DRAWER","HIGHLIGHTS_DEFAULT","BOOK_IT_NAV","URGENCY_COMMITMENT","URGENCY_COMMITMENT_SIDEBAR","BOOK_IT_SIDEBAR","EDUCATION_FOOTER_BANNER","POLICIES_DEFAULT","BOOK_IT_FLOATING_FOOTER"],"checkIn":null,"checkOut":null,"p3ImpressionId":"p3_1608841700_z2VzPeybmBEdZG20"}}
        # &extensions={"persistedQuery":{"version":1,"sha256Hash":"625a4ba56ba72f8e8585d60078eb95ea0030428cac8772fde09de073da1bcdd0"}}
        query = {
            'operationName': 'PdpPlatformSections',
            'locale':        'en',
            'currency':      'USD',
            'variables':     {
                'request': {
                    'id':                            listing['listing']['id'],
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
                    'sectionIds':                    [
                        'EDUCATION_FOOTER_BANNER_MODAL', 'BOOK_IT_CALENDAR_SHEET', 'BOOK_IT_CALENDAR_DRAWER',
                        'HIGHLIGHTS_DEFAULT', 'BOOK_IT_NAV', 'URGENCY_COMMITMENT', 'URGENCY_COMMITMENT_SIDEBAR',
                        'BOOK_IT_SIDEBAR', 'EDUCATION_FOOTER_BANNER', 'POLICIES_DEFAULT', 'BOOK_IT_FLOATING_FOOTER'
                    ],
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

        self._fix_json_params(query)
        url = self._build_airbnb_url(_api_path, query)
        headers = self._get_search_headers()

        return scrapy.Request(url, callback=self._spider.parse_listing_contents, headers=headers)
