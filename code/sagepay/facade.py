import hashlib
import pprint

from django.db.models import get_model

from oscar.apps.payment.exceptions import PaymentError, InvalidGatewayRequestError

from .gateway import Gateway
from .models import TransactionRegistrationServerResponse, SagePayTransaction, CountryCode, NotificationPostResponse, Token
from .exceptions import GatewayException, TransactionDoesNotExistException
from .utils import utf8_truncate
from .core import TransactionNotificationPostResponse
from .settings import *

BillingAddress = get_model('order', 'BillingAddress')
OscarCountry = get_model('address', 'Country')


class Facade(object):
    """
    A bridge between oscar's and sagepay's objects and the core gateway object
    """

    def __init__(self):
        self.gateway = Gateway(SAGEPAY_PROFILE, NOTIFICATION_URL, SAGE_SERVER_URL)

    def authorize(self, order_number, basket, amount, shipping_address, billing_address=None, save_card=False, card_token=None):
        """
        Starts the process of authorizing a payment with SagePay

        :param order_number: Oscar associated order number
        :type order_number: str
        :param basket: Oscar associated basket
        :type basket: :class:`oscar.apps.basket.models.Basket` instance
        :param amount: total to be paid (excluding SagePay surchages)
        :type amount: decimal
        :param billing_address: customer billing address
        :type billing_address: dict
        :param shipping_address: customer shipping address
        :type shipping_address: `oscar.apps.address.models.UserAddress` instance
        :param token: generate and return a credit card token (to save the credit card details in a safe way)
        :type token: bool
        """
        description = ''
        for l in basket.lines.all():
            description = description + l.product.title + ', '

        # billing address can be "None" if a saved card is used, let's build the billing_address dictionary from the token
        if card_token is not None and billing_address is None:
            token = Token.objects.get(token=card_token)
            tr = token.sagepaytransaction_set.all()[0]
            billing_address = {
                               'first_name': tr.billing_firstnames,
                               'last_name': tr.billing_surname,
                               'line1': tr.billing_address1,
                               'line2': tr.billing_address2,
                               'line4': tr.billing_city,
                               'postcode': tr.billing_postcode,
                               'country': tr.billing_country
                               }

        # shipping address can be none for digital products, let's use billing address then
        if shipping_address is None:
            delivery_firstnames = billing_address['first_name']
            delivery_surname = billing_address['last_name']
            delivery_address1 = billing_address['line1']
            delivery_address2 = billing_address['line2']
            delivery_city = billing_address['line4']
            delivery_postcode = billing_address['postcode']
            if card_token is not None:
                delivery_country = CountryCode.objects.get(name__iexact=billing_address['country'].name)
            else:
                delivery_country = CountryCode.objects.get(name__iexact=billing_address['country'].printable_name)
        else:
            delivery_firstnames=shipping_address.first_name
            delivery_surname=shipping_address.last_name
            delivery_address1=shipping_address.line1
            delivery_address2=shipping_address.line2
            delivery_city=shipping_address.line4
            delivery_postcode=shipping_address.postcode
            delivery_country = CountryCode.objects.get(name__iexact=shipping_address.country.printable_name)

        # the sagepay transaction must be saved in the database before proceeding
        transaction = SagePayTransaction(
                oscar_basket=basket,
                oscar_order=order_number,
                tx_type='PAYMENT',
                amount=amount,
                currency='GBP',
                description=utf8_truncate(description, 100),
                delivery_firstnames=delivery_firstnames,
                delivery_surname=delivery_surname,
                delivery_address1=delivery_address1,
                delivery_address2=delivery_address2,
                delivery_city=delivery_city,
                delivery_postcode=delivery_postcode,
                delivery_country=delivery_country,
                delivery_state='',
                delivery_phone='',
                customer_email='',
            )

        # billing details are not passed if a stored credit card is used
        if billing_address is not None:
            transaction.billing_firstnames = billing_address['first_name']
            transaction.billing_surname = billing_address['last_name']
            transaction.billing_address1 = billing_address['line1']
            transaction.billing_address2 = billing_address['line2']
            transaction.billing_city = billing_address['line4']
            transaction.billing_postcode = billing_address['postcode']
            transaction.billing_state = ''
            transaction.billing_phone = ''
            if card_token is not None:
                transaction.billing_country = CountryCode.objects.get(name__iexact=billing_address['country'].name)
            else:
                transaction.billing_country = CountryCode.objects.get(name__iexact=billing_address['country'].printable_name)
        else:
            transaction.billing_firstnames = shipping_address.first_name
            transaction.billing_surname = shipping_address.last_name
            transaction.billing_address1 = shipping_address.line1
            transaction.billing_address2 = shipping_address.line2
            transaction.billing_city = shipping_address.line4
            transaction.billing_postcode = shipping_address.postcode
            transaction.billing_country = CountryCode.objects.get(name__iexact=shipping_address.country.printable_name)
            transaction.billing_state = ''
            transaction.billing_phone = ''
        if card_token is not None:
            transaction.token = Token.objects.get(token=card_token)
        transaction.save()
        return self._register_payment(transaction, save_card)

    def _register_payment(self, transaction, saved_card):
        """
        :param transaction:
        :type transaction: :class:`sagepay.models.SagePayTransaction` instance
        :param token: generate and return a credit card token (to save the credit card details in a safe way)
        :type token: bool
        """
        try:
            response, status = self.gateway.register_payment(transaction, saved_card)
            if response.is_successful:
                return self._save_server_registration_response(transaction, response)
            else:
                raise InvalidGatewayRequestError('Sage server wrong request, this should happen in development only: %s' % response)
        except GatewayException:
            raise PaymentError('Unable to contact SagePay server')


    def _save_server_registration_response(self, transaction, response):
        """
        :param transaction: the ongoing transaction transaction
        :type transaction: class:`sagepay.models.SagePayTransaction` instance
        :param response: registration payment response
        :type response: :class:`gateway.Gateway.register_payment` response
        :returns: str -- transaction id
        """
        transaction_response = TransactionRegistrationServerResponse(
            vps_protocol=response['VPSProtocol'],
            vps_tx_id=response['VPSTxId'],
            security_key=response['SecurityKey'],
            status=response['Status'],
            status_detail=response['StatusDetail'],
            next_url=response['NextURL']
        )
        transaction_response.save()
        # update the transaction model with the sage response model's id
        transaction.transaction_registration_server_response = transaction_response
        transaction.save()
        return response['VPSTxId']

    def _sage_transaction_from_tx_id(self, tx_id):
        """
        Return the SagePay transaction from its id

        :param tx_id: Id of SagePay transaction
        :type tx_id: str
        :returns: :class:`sagepay.models.SagePayTransaction` instance
        """
        transaction_registration_server_response = TransactionRegistrationServerResponse.objects.get(vps_tx_id=tx_id)
        sage_transaction = SagePayTransaction.objects.get(
            transaction_registration_server_response = transaction_registration_server_response
        )
        return sage_transaction

    def order_basket_amount_from_tx_id(self, tx_id):
        """
        Return the Oscar order id, Oscar basket id and amount from the SagePay transaction id

        :param tx_id: Id of SagePay transaction
        :type tx_id: str
        :returns: tuple - (order_id, basket, amount)
        """
        sage_transaction = self._sage_transaction_from_tx_id(tx_id)
        order_id = sage_transaction.oscar_order
        basket = sage_transaction.oscar_basket
        amount = sage_transaction.amount
        return (order_id, basket, amount)

    def user_from_basket_id(self, basket_id):
        pass

    def check_transaction_notification(self, response):
        """
        Check if the SagePay server transaction notification is valid (Md5 hash) and build the response for the right status

        :param response: SagePay transaction notification response
        :type response: dict
        :returns: str --  In the right Sage format
        """
        tresponse = TransactionNotificationPostResponse(response)
        # whatever sage says we save the response in the database and link it to the original transaction
        post_response_model = self._save_transaction_notification_post_response(tresponse)
        try:
            validate = self._validate_transaction_notification(tresponse)
        except TransactionDoesNotExistException:
            return "Status=ERROR\r\nRedirectURL=http://109.204.98.107/checkout/thankyou/\r\n&StatusDetail=Transaction doesn't exist\r\n"
        # sage post response has been tampered with!!
        if not validate:
            reply_text = "Status=INVALID\r\nRedirectURL=http://109.204.98.107/checkout/thankyou/\r\n&StatusDetail=Hash not matching\r\n"
            post_response_model.hash_match = False
            post_response_model.replied = True
            post_response_model.reply_text = reply_text
            post_response_model.save()
            return reply_text
        if tresponse.ok:
            redirect_url = THANK_YOU_URL + tresponse['VPSTxId']
            reply_text = "Status=OK\r\nRedirectURL=%s\r\n" % (redirect_url)
            post_response_model.hash_match = True
            post_response_model.replied = True
            post_response_model.reply_text = reply_text
            post_response_model.save()
            return reply_text
        elif tresponse.notauthed:
            redirect_url = ERROR_URL + '1'
            reply_text = "Status=OK\r\nRedirectURL=%s\r\n" % (redirect_url)
            post_response_model.replied = True
            post_response_model.reply_text = reply_text
            return reply_text
        elif tresponse.abort:
            redirect_url = ERROR_URL + '2'
            reply_text = "Status=OK\r\nRedirectURL=%s\r\n" % (redirect_url)
            post_response_model.replied = True
            post_response_model.reply_text = reply_text
            return reply_text
        elif tresponse.rejected:
            redirect_url = ERROR_URL + '3'
            reply_text = "Status=OK\r\nRedirectURL=%s\r\n" % (redirect_url)
            post_response_model.replied = True
            post_response_model.reply_text = reply_text
            return reply_text
        elif tresponse.authenticated:
            return ''
        elif tresponse.error:
            return ''

    def _save_transaction_notification_post_response(self, response):
        """
        Save the SagePay transaction notification response and link it to the initial transaction

        :param response: SagePay transaction notification response
        :type response: class:`sagepay.models.TransactionNotificationResponse` instance
        :returns: class:`sagepay.models.NotificationPostResponse` instance
        """
        post_response_model = NotificationPostResponse(
            vps_protocol=response.get('VPSProtocol',''),
            tx_type=response.get('TxType',''),
            vendor_tx_code=response.get('VendorTxCode',''),
            vps_tx_id=response.get('VPSTxId',''),
            status=response.get('Status',''),
            status_detail=response.get('StatusDetail',''),
            tx_auth_no=response.get('TxAuthNo',''),
            avscv2=response.get('AVSCV2',''),
            address_result=response.get('AddressResult',''),
            postcode_result=response.get('PostCodeResult',''),
            cv2_result=response.get('CV2Result',''),
            gift_aid=response.get('GiftAid',''),
            threed_secure_status=response.get('3DSecureStatus',''),
            cavv=response.get('CAVV',''),
            card_type=response.get('CardType',''),
            last_4_digits=response.get('Last4Digits',''),
            decline_code=response.get('DeclineCode',''),
            expiry_date=response.get('ExpiryDate',''),
            bank_auth_ode=response.get('BankAuthCode', '')
        )
        post_response_model.save()
        # link the sage transaction to the post notification
        sage_transaction = self._sage_transaction_from_tx_id(response['VPSTxId'])
        sage_transaction.notification_post_response = post_response_model
        sage_transaction.save()
        # the user wants to save the credit card details
        if 'Token' in response:
            token = self._save_credit_card_token(response, sage_transaction)
            sage_transaction.token = token
            sage_transaction.save()
        return post_response_model

    def _save_credit_card_token(self, response, sage_transaction):
        """
        Save the

        :param response: SagePay transaction notification response
        :type response: class:`sagepay.models.TransactionNotificationResponse` instance
        :returns:
        """
        user = sage_transaction.oscar_basket.owner
        token = response['Token']
        last_4_digits = response['Last4Digits']
        card_type = response['CardType']
        expiry_date = response['ExpiryDate']
        token_object = Token(token=token, user=user, last_4_digits=last_4_digits, card_type=card_type, expiry_date=expiry_date)
        token_object.save()

    def check_credit_card_exist(self):
        pass

    def get_credit_cards(self, user):
        return Token.objects.filter(user=user)

    def delete_token(self, token):
        """
        Delete the token

        :param token: Token to be deleted
        :type token: :class:`sagepay.models.Token` instance
        :returns: boolean
        """
        return  self.gateway.delete_token(token)

    def _validate_transaction_notification(self, tresponse):
        """
        Validate the response of sage server using the MD5 hash (page 66 of sage manual)

        :param notification: SagePay transaction notification response
        :type notification: class:`sagepay.models.TransactionNotificationResponse` instance
        :returns: Boolean
        """
        tx_id = tresponse['VPSTxId']
        try:
            transaction_registration_server_response = TransactionRegistrationServerResponse.objects.get(vps_tx_id=tx_id)
        except TransactionRegistrationServerResponse.DoesNotExist:
            raise TransactionDoesNotExistException('The transaction id doesn''t match our database')
        vendor_name = transaction_registration_server_response.vendor.lower()
        security_key = transaction_registration_server_response.security_key
        # rebuild the post
        post = tresponse.post_format(vendor_name, security_key)
        hash = hashlib.md5(post)
        # md5 hash returned from sage server is uppercase
        hash = hash.hexdigest().upper()
        if hash == tresponse['VPSSignature']:
            return True
        else:
            return False

    def save_billing_address_from_order(self, order):
        """
        Save the billing address in the oscar order's model, for some reason oscar doesn't do that

        :param order: Oscar associated order number
        :type order: class:`oscar.apps.order.models.Order` instance
        :returns:
        """
        transaction = SagePayTransaction.objects.get(oscar_order=order.number)
        country = OscarCountry.objects.get(printable_name__iexact=transaction.billing_country.name)
        billing_address = BillingAddress(
             first_name=transaction.billing_firstnames,
             last_name=transaction.billing_surname,
             line1=transaction.billing_address1,
             line2=transaction.billing_address2,
             line4=transaction.billing_city,
             postcode=transaction.billing_postcode,
             country=country
        )
        billing_address.save()
        order.billing_address = billing_address
        order.save()

