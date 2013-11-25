import pprint

from decimal import Decimal

import requests

from .exceptions import GatewayException
from .core import Response
from .settings import VENDOR, PROTOCOL, DELETE_TOKEN_URL

class Gateway(object):
    """
    Handle the communication with Sage server

    :param profile: SagePay server profile parameter (LOW or NORMAL)
    :type profile: str
    :param notification_url: SagePay server notification URL parameter
    :type notification_url: str
    :param sage_server_url: SagePay server fully qualified URL
    :type sage_server_url: str
    """
    def __init__(self, profile, notification_url, sage_server_url):
        self.profile = profile
        self.notification_url = notification_url
        self.sage_server_url = sage_server_url

    def post(self, url, data):
        try:
            t = requests.post(url, data=data)
            return Response(t.text)
        except (requests.ConnectionError, requests.Timeout):
            raise GatewayException('Something went wrong while contacting the SagePay server')

    def register_payment(self, transaction, save_card):
        """
        Start a payment registration process

        :param transaction: The transaction saved into the database
        :type transaction: :class:`sagepay.models.SagePayTransaction` instance
        :param token: generate or not a token
        :type token: bool
        :param store_token: save or not the token
        :type store_token: bool
        :returns: Tuple -- (:class:`sagepay.core.Response` instance, boolean) Boolean is False if the gateway failed to contact the server
        """
        data = dict(
            Profile=self.profile,
            VPSProtocol=transaction.vps_protocol,
            TxType=transaction.tx_type,
            Vendor=transaction.vendor,
            VendorTxCode=transaction.vendor_tx_code,
            Amount=transaction.amount.quantize(Decimal('1.00')),
            Currency=transaction.currency,
            Description=transaction.description,
            NotificationURL=self.notification_url,
            BillingSurname=transaction.billing_surname,
            BillingFirstnames=transaction.billing_firstnames,
            BillingAddress1=transaction.billing_address1,
            BillingCity=transaction.billing_city,
            BillingPostCode=transaction.billing_postcode,
            BillingCountry=transaction.billing_country.sagecode,
            BillingState=transaction.billing_state,
            BillingPhone=transaction.billing_phone,
            DeliverySurname=transaction.delivery_surname,
            DeliveryFirstnames=transaction.delivery_firstnames,
            DeliveryAddress1=transaction.delivery_address1,
            DeliveryCity=transaction.delivery_city,
            DeliveryPostCode=transaction.delivery_postcode,
            DeliveryCountry=transaction.delivery_country.sagecode,
            DeliveryState=transaction.delivery_state,
            DeliveryPhone=transaction.delivery_phone,
            CustomerEmail=transaction.customer_email,
            Basket=transaction.basket,
            AllowGiftAid=int(transaction.allow_gift_aid),
            StoreToken=1,
        )
        if save_card is True:
            data['CreateToken'] = int(save_card)
        if transaction.token is not None:
            data['Token'] = transaction.token.token_transaction_format

        response = self.post(self.sage_server_url, data)
        if response.is_successful:
            return (response, True)
        else:
            return (response, False)


    def delete_token(self, token):
        """

        :param token: Token to be deleted
        :type token: :class:`sagepay.models.Token` instance
        :returns: boolean
        """
        data = dict(
            VPSProtocol=PROTOCOL,
            TxType='REMOVETOKEN',
            Vendor=VENDOR,
            Token=token.token
        )
        pprint.pprint(data)
        response = self.post(DELETE_TOKEN_URL, data=data)
        if response.is_successful:
            return True
        else:
            return False



