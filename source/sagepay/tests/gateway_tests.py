from types import TupleType, BooleanType

from django.test import TestCase
import mock

from sagepay.models import SagePayTransaction, CountryCode
from sagepay.gateway import Gateway, Response
from sagepay.exceptions import GatewayException


class GatewayResponseTest(TestCase):
    SAGE_SERVER_REGISTRATION_OK_RESPONSE = """VPSProtocol=3.00
Status=OK
StatusDetail=2014 : The Transaction was Registered Successfully.
VPSTxId={1A960910-5F36-3421-24DE-65EF52C13380}
SecurityKey=U5NX3V0WG9
NextURL=https://test.sagepay.com/gateway/service/cardselection?vpstxid={1A960910-5F36-3421-24DE-65EF52C13380}"""

    SAGE_SERVER_REGISTRATION_INVALID_RESPONSE = """VPSProtocol=3.00
Status=INVALID
StatusDetail=3011 : The NotificationURL format is invalid."""

    def setUp(self):
        self.response = Response(self.SAGE_SERVER_REGISTRATION_OK_RESPONSE)
        self.invalid_response = Response(self.SAGE_SERVER_REGISTRATION_INVALID_RESPONSE)

    def test_is_successful_property(self):
        self.assertEqual(True, self.response.is_successful)
        self.assertEqual(False, self.invalid_response.is_successful)


class GatewayTest(TestCase):
    SAGEPAY_SERVER = 'https://test.sagepay.com/gateway/service/vspserver-register.vsp'
    WRONG_URL = 'http://fdsfdsfdsf.com'
    PROFILE = 'LOW'
    NOTIFICATION_URL = 'http://test.com'
    WRONG_NOTIFICATION_URL = 'test.com'

    def setUp(self):
        uk = CountryCode(name='United Kingdom', code='GB')
        uk.save()
        self.transaction = SagePayTransaction(
                amount=10,
                oscar_basket = 1,
                oscar_order = 1,
                oscar_user=1,
                description='test',
                billing_firstnames='Alex',
                billing_surname='udox',
                billing_address1='test address',
                billing_city='London',
                billing_postcode='12424145',
                billing_country=uk,
                delivery_firstnames='Alex',
                delivery_surname='udox',
                delivery_address1='test address',
                delivery_city='London',
                delivery_postcode='12424145',
                delivery_country=uk,
        )
        self.transaction.save()

    def test_register_payment_method_return_type(self):
        gateway = Gateway(self.PROFILE, self.NOTIFICATION_URL, self.SAGEPAY_SERVER)
        register = gateway.register_payment(self.transaction)
        tuple_type = type(register)
        boolean_type = type(register[1])
        self.assertIs(TupleType, tuple_type, 'Gateway.register_payment must return a tuple')
        self.assertIsInstance(register[0], Response, 'The first element of Gateway.register_payment must be a gateway.Response instance')
        self.assertIs(BooleanType, boolean_type, 'The second element of Gateway.register_payment must a boolean')

    def test_register_payment_method_sage_response_status_successful(self):
        gateway = Gateway(self.PROFILE, self.NOTIFICATION_URL, self.SAGEPAY_SERVER)
        register = gateway.register_payment(self.transaction)
        self.assertEqual(register[0].is_successful, True, 'Status response should have returned True, something went wrong with the payment registration')

    def test_register_payment_method_sage_response_status_not_successful(self):
        gateway = Gateway(self.PROFILE, self.WRONG_NOTIFICATION_URL, self.SAGEPAY_SERVER)
        register = gateway.register_payment(self.transaction)
        self.assertEqual(register[0].is_successful, False, 'Status response should have returned False, something went wrong with the payment registration')

    def test_register_payment_method_exception(self):
        gateway = Gateway(self.PROFILE, self.NOTIFICATION_URL, self.WRONG_URL)
        self.assertRaises(GatewayException, gateway.register_payment, self.transaction)
