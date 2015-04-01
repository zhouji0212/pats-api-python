# -*- coding: utf-8 -*-

# Copyright (c) 2015, Brendan Quinn, Clueful Media Ltd / JT-PATS Ltd
#
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
PATS Python library - Buyer side - Brendan Quinn Dec 2014

Based on Mediaocean PATS API documented at https://developer.mediaocean.com/
"""

from collections import OrderedDict
from httplib import HTTPSConnection
import json
import os
import re
import string
from urllib import urlencode
from .core import PATSAPIClient, PATSException, CampaignDetails, InsertionOrderDetails

AGENCY_API_DOMAIN = 'prisma-demo.api.mediaocean.com'

VERSION = '0.1'

class PATSBuyer(PATSAPIClient):
    agency_id = None

    def __init__(self, agency_id=None, api_key=None):
        """
        Create a new buyer-side PATS API object.

        Parameters:
        - agency_id (required) : ID of the agency (buyer) whose catalogue
          you are updating.
        - api_key (required) : API Key with buyer access
        """
        super(PATSBuyer, self).__init__(api_key)
        if agency_id == None:
            raise PATSException("Agency (aka buyer) ID is required")
        self.agency_id = agency_id

    def create_campaign(self, campaign_details=None, **kwargs):
        """
        Create an agency-side campaign, which is then used to send RFPs and orders.
        "campaign_details" must be a CampaignDetails instance.
        """
        if not isinstance(campaign_details, CampaignDetails):
            raise PATSException(
                "The campaign_details parameter should be a CampaignDetails instance")

        # Create the http object
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1.0+json',
            'X-MO-Person-ID': campaign_details.person_id,
            'X-MO-Company-ID': campaign_details.company_id,
            'X-MO-Organization-ID': campaign_details.organisation_id
        }
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/campaigns",
            extra_headers,
            campaign_details.json_repr()
        )
        campaignId = js['campaignId']
        return campaignId

    def view_campaign_detail(self, sender_user_id, campaign_public_id):
        # aka "view RFPs for campaign"
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/campaign/%s/rfps" % (self.agency_id, campaign_public_id),
            extra_headers
        )
        return js

    def submit_rfp(self, sender_user_id=None, campaign_public_id=None, budget_amount=None, start_date=None, end_date=None, respond_by_date=None, comments="", publisher_id=None, publisher_emails=None, media=None, strategy=None, requested_products=None):
        """
        Send an RFP to one or more publishers.
        Can optionally include product IDs.
        """
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        data = {
            'agencyPublicId': self.agency_id,
            'campaignPublicId': campaign_public_id,
            # the docs say "budgets" : { "amount" ... in "comma separated format"
            # what they actually mean is "budgets": [ 1000, 2000, 3000 ]
            'budgets': [ budget_amount ], # just handle one for now
            'startDate': start_date.strftime("%Y-%m-%d"),
            'endDate': end_date.strftime("%Y-%m-%d"),
            'responseDueDate': respond_by_date.strftime("%Y-%m-%d"),
            'comments': comments,
            'publisherRecipients': [
                {
                    'publisherPublicId': publisher_id,
                    'emails': publisher_emails,
                }
            ],
            'media': media, # Array of one or more of 'Print', 'Online'
            'strategy': strategy, # must be one of defined set of terms
            'requestedProducts': requested_products,
            # TODO: handle attachments
        }
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/agencies/%s/campaigns/%s/rfps" % (self.agency_id, campaign_public_id),
            extra_headers,
            json.dumps(data)
        )
        return js

    def submit_product_rfp(self):
        # TODO
        # /agencies/{agencyPublicId}/campaigns/{campaignPublicId}/rfps
        pass

    def view_rfp_detail(self, sender_user_id=None, rfp_id=None):
        if rfp_id is None:
            raise PATSException("RFP ID is required")
        if sender_user_id is None:
            raise PATSException("Sender User ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/rfps/%s" % (self.agency_id, rfp_id),
            extra_headers
        )
        return js

    def get_rfp_attachment(self, sender_user_id=None, rfp_id=None, attachment_id=None):
        # is this for both buyer and seller side?
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/rfps/%s/attachments/%s" % (self.agency_id, rfp_id, attachment_id),
            extra_headers
        )
        return js

    def search_rfps(self, sender_user_id):
        # /agencies/35-1-1W-1/rfps?advertiserName=Jaguar Land Rover&campaignUrn=someUrn&rfpStartDate=2014-08-10&rfpEndDate=2015-01-10&responseDueDate=2015-08-25&status=SENT
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        # TODO
        pass

    def get_proposal_attachment(self, sender_user_id=None, proposal_public_id=None, attachment_id=None):
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.rfps-v3+json',
            'X-MO-User-Id': sender_user_id
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/proposals/%s/attachments/%s" % (self.agency_id, proposal_public_id, attachment_id),
            extra_headers
        )
        return js

    def return_proposal(self):
        # TODO
        pass

    def list_products(self, vendor_id=None, start_index=None, max_results=None, include_logo=False):
        """
        List products in a vendor's product catalogue.

        The parameters are :
        - vendor_id (required): ID of the vendor (publisher) whose catalogue
          you are requesting.
        - start_index (optional): First product to load (if doing paging)
        - max_results (optional):
        """
        if vendor_id is None:
            raise PATSException("Vendor ID is required")

        params = {}
        if start_index:
            params.update({'start_index' : start_index})
        if max_results:
            params.update({'max_results' : max_results})
        if include_logo:
            params.update({'include_logo' : include_logo})
        params = urlencode(params)

        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/vendors/%s/products/?%s" % (self.agency_id, vendor_id, params),
            extra_headers,
            json.dumps(data)
        )
        if js['validationResults']:
            raise PATSException("Product ID "+js['validationResults'][0]['productId']+": error is "+js['validationResults'][0]['message'])
        productId = js['products'][0]['productPublicId']
        return js

    def create_order(self, **kwargs):
        """
        create a print or digital order in PATS.
        agency_id: PATS ID of the buying agency (eg 35-IDSDKAD-7)
        company_id: PATS ID of the buying company (eg PATS3)
        person_id: (optional?) PATS ID of the person sending the order (different
            from the person named as the buyer contact in the order)
        insertion_order_details: info about the insertion order (must be an InsertionOrderDetails object)
        """
        if kwargs.get('company_id') == None:
            raise PATSException("Company ID is required")
        if kwargs.get('insertion_order_details') == None:
            raise PATSException("Insertion Order object is required")
        insertion_order = kwargs.get('insertion_order_details', None)
        if not isinstance(insertion_order, InsertionOrderDetails):
            raise PATSException("insertion_order_details must be an instance of InsertionOrderDetails")

        extra_headers = {}
        extra_headers.update({
            'Accept': 'application/vnd.mediaocean.prisma-v1.0+json',
            'X-MO-Company-ID': kwargs.get('company_id'),
            'X-MO-Person-ID': kwargs.get('person_id'),
            'X-MO-Organization-ID': self.agency_id
        })

        # order payload
        data = {
            'externalCampaignId':kwargs.get('external_campaign_id', None),
            'mediaType':kwargs.get('media_type', 'PRINT'),
            'insertionOrder':insertion_order.dict_repr()
        }
        # technically line items are optional!
        if kwargs.get('line_items'):
            line_items = []
            for line_item in kwargs['line_items']:
                line_item.setOperation('Add')
                line_items.append(line_item.dict_repr())
            data.update({
                'lineItems':line_items
            })

        # send request
        js = self._send_request(
            "PUT",
            AGENCY_API_DOMAIN,
            "/order/send",
            extra_headers,
            json.dumps(data)
        )
        return js

    def view_orders(self, buyer_email=None, start_date=None, end_date=None):
        """
        As a buyer, view all orders I have sent.
        """
        if start_date == None:
            raise PATSException("Start date is required")
        if buyer_email == None:
            raise PATSException("Buyer email is required")

        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-User-Id': buyer_email
        }

        path = '/agencies/%s/orders/revisions' % self.agency_id
        if start_date and end_date:
            # not sure if you can have one or the other on its own?
            path += "?startDate=%s&endDate=%s" % (
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        # TODO: Parse the response and return something more intelligible
        return js

        
    def view_order_detail(self, buyer_email=None, order_public_id=None):
        # /agencies/{agency public id}/orders/{External Order Id}/revisions
        if buyer_email == None:
            raise PATSException("Buyer email is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1+json',
            'X-MO-User-Id': buyer_email
        }
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            "/agencies/%s/orders/%s/revisions" % (self.agency_id, order_public_id),
            extra_headers
        )
        return js

    def view_order_status(self, person_id=None, company_id=None, campaign_id=None, order_id=None, version=None):
        # /order/status/{externalCampaignId}/{orderId}/{version}
        if company_id == None:
            raise PATSException("Company ID is required")
        if campaign_id == None:
            raise PATSException("Campaign ID is required")
        if order_id == None:
            raise PATSException("Order ID is required")
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.prisma-v1+json',
            'X-MO-Company-ID': company_id,
            'X-MO-Organization-ID': self.agency_id
        }
        if person_id:
            extra_headers.update({
                'X-MO-Person-ID': person_id,
            })
        path = "/order/status/%s/%s" % (campaign_id, order_id)
        if version:
            path += "/"+version
        js = self._send_request(
            "GET",
            AGENCY_API_DOMAIN,
            path,
            extra_headers
        )
        return js
        
    def return_order_revision(self, order_public_id, order_major_version, order_minor_version, buyer_email, seller_email, revision_due_date, comment):
        # TODO: allow attachments
        # /agencies/{agency public id}/orders/{external public id}/revisions/return 
        extra_headers = {
            'Accept': 'application/vnd.mediaocean.order-v1.0+json',
            'X-MO-User-ID': buyer_email
        }
        data = {
            'majorVersion': order_major_version,
            'minorVersion': order_minor_version,
            'revisionDueBy': revision_due_date.strftime("%Y-%m-%d"),
            'comment': comment,
            'email': seller_email,
            'orderAttachments': [], # leave it blank for now
        }
        js = self._send_request(
            "POST",
            AGENCY_API_DOMAIN,
            "/agencies/%s/orders/%s/revisions/return" % (self.agency_id, order_public_id),
            extra_headers,
            json.dumps(data)
        )
        return js
