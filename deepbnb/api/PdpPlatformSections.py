import scrapy

from deepbnb.api.ApiBase import ApiBase


class PdpPlatformSections(ApiBase):
    SECTION_IDS = [
        'AMENITIES_DEFAULT',
        'DESCRIPTION_DEFAULT',
        'HOST_PROFILE_DEFAULT',
        'LOCATION_DEFAULT',
        'POLICIES_DEFAULT',
    ]

    def api_request(self, listing_id: str):
        """Generate scrapy.Request for listing page."""
        _api_path = '/api/v3/PdpPlatformSections'
        query = {
            'operationName': 'PdpPlatformSections',
            'locale':        'en',
            'currency':      'USD',
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

        self._fix_json_params(query)
        url = self._build_airbnb_url(_api_path, query)
        headers = self._get_search_headers()

        return scrapy.Request(url, callback=self._spider.parse_listing_contents, headers=headers)
