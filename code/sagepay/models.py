import hashlib

from django.db import models
from django.db.models import get_model

from model_utils import Choices
from model_utils.models import TimeStampedModel

from .settings import VENDOR, PROTOCOL, DEFAULT_CURRENCY

Basket = get_model('basket', 'Basket')


class CountryCode(models.Model):
    """
    SagePay uses the ISO 3166-1 country code
    it's better to have it as separated model and automatically import the codes using
    utils.populate_country_code
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=2, unique=True)

    def __unicode__(self):
        return u'%s - %s' % (self.name, self.code)

    @property
    def sagecode(self):
        return self.code


class Token(TimeStampedModel):
    token = models.CharField(max_length=38)
    user = models.ForeignKey('auth.User', related_name='token')
    last_4_digits = models.CharField(max_length=4)
    card_type = models.CharField(max_length=15)
    expiry_date = models.CharField(max_length=4)

    @property
    def obfuscated_card(self):
        return u"xxxx-xxxx-xxxx-{0:s}".format(self.last_4_digits)

    @property
    def expiry_date_formatted(self):
        return u"{0:s}/20{1:s}".format(self.expiry_date[0:2], self.expiry_date[2:])

    @property
    def summary(self):
        return u"{0:s} {1:s} ({2:s})".format(self.card_type, self.obfuscated_card, self.expiry_date_formatted)

    @property
    def token_transaction_format(self):
        return self.token

    def __unicode__(self):
        return u"{0:s} ({1:s})".format(self.token, self.summary)


class TransactionRegistrationServerResponse(TimeStampedModel):
    """
    This class contains the field of Step 3
    """
    vps_protocol = models.CharField(max_length=4)
    vendor = models.CharField(max_length=15, default=VENDOR)
    vps_tx_id = models.CharField(max_length=38)
    security_key = models.CharField(max_length=10)
    status = models.CharField(max_length=20)
    status_detail = models.CharField(max_length=255)
    next_url = models.URLField(max_length=255)

    def __unicode__(self):
        return self.vps_tx_id


class NotificationPostResponse(TimeStampedModel):
    """
    This class contains the field of Step 9
    """
    vps_protocol = models.CharField(max_length=4)
    tx_type = models.CharField(max_length=15)
    vendor_tx_code = models.CharField(max_length=40)
    vps_tx_id = models.CharField(max_length=38)
    status = models.CharField(max_length=20)
    status_detail = models.CharField(max_length=255)
    tx_auth_no = models.CharField(max_length=10, null=True)
    avscv2 = models.CharField(max_length=50, null=True)
    address_result = models.CharField(max_length=20)
    postcode_result = models.CharField(max_length=20)
    cv2_result = models.CharField(max_length=20)
    gift_aid = models.BooleanField()
    threed_secure_status = models.CharField(max_length=50)
    cavv = models.CharField(max_length=32)
    card_type = models.CharField(max_length=15)
    last_4_digits = models.CharField(max_length=4)
    decline_code = models.CharField(max_length=2)
    expiry_date = models.CharField(max_length=4)
    bank_auth_ode = models.CharField(max_length=6)
    # internal use fields
    hash_match = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)
    reply_text = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.vps_tx_id


class SagePayTransaction(TimeStampedModel):
    """
    Main sagepay transaction model. It has everything saved.
    """
    TX_TYPE = Choices(('PAYMENT', 'PAYMENT'),
                      ('DEFERRED', 'DEFERRED'),
                      ('AUTHENTICATE', 'AUTHENTICATE'))

    # oscar fields
    oscar_basket = models.ForeignKey(Basket, related_name='oscar_basket')
    oscar_order = models.PositiveIntegerField()

    # sage fields
    vps_protocol = models.CharField(max_length=4, default=PROTOCOL)
    vendor = models.CharField(max_length=15, default=VENDOR)
    vendor_tx_code = models.CharField(max_length=40, null=True, blank=True, help_text='This will be automatically generated')
    tx_type = models.CharField(choices=TX_TYPE, default=TX_TYPE.PAYMENT, max_length=15)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    #
    currency = models.CharField(max_length=3, default=DEFAULT_CURRENCY)
    description = models.TextField(max_length=100)
    basket = models.TextField(max_length=7500, blank=True, null=True)
    #
    billing_firstnames = models.CharField(max_length=20, blank=True, null=True)
    billing_surname = models.CharField(max_length=20, blank=True, null=True)
    billing_address1 = models.CharField(max_length=100, blank=True, null=True)
    billing_address2 = models.CharField(max_length=100, blank=True, null=True)
    billing_city = models.CharField(max_length=40, blank=True, null=True)
    billing_postcode = models.CharField(max_length=10, blank=True, null=True)
    billing_country = models.ForeignKey(CountryCode, related_name='billing', blank=True, null=True)
    billing_state = models.CharField(max_length=2, blank=True, null=True)
    billing_phone = models.CharField(max_length=20, blank=True, null=True)
    #
    delivery_firstnames = models.CharField(max_length=20)
    delivery_surname = models.CharField(max_length=20)
    delivery_address1 = models.CharField(max_length=100)
    delivery_address2 = models.CharField(max_length=100, blank=True, null=True)
    delivery_city = models.CharField(max_length=40)
    delivery_postcode = models.CharField(max_length=10)
    delivery_country = models.ForeignKey(CountryCode, related_name='delivery')
    delivery_state = models.CharField(max_length=2, blank=True, null=True)
    delivery_phone = models.CharField(max_length=20, blank=True, null=True)
    #
    customer_email = models.CharField(max_length=255, blank=True, null=True)
    allow_gift_aid = models.BooleanField( default=False)

    # fields returned by sage server, they are all null=True because they get populated during the process
    transaction_registration_server_response = models.ForeignKey(TransactionRegistrationServerResponse, null=True, blank=True)
    notification_post_response = models.ForeignKey(NotificationPostResponse, null=True, blank=True)

    #
    token = models.ForeignKey(Token, null=True, blank=True)

    def save(self, force_insert=False, force_update=False, using=None):
        """
        VendorTxCode MUST be unique for each transaction issued to SagePay.
        We can use the id but who never knows.
        Let's automatically create a md5 hash with id+created
        """
        hash = hashlib.md5(str(self.id)+self.created.isoformat())
        self.vendor_tx_code = hash.hexdigest()
        super(SagePayTransaction, self).save(force_update, force_update, using)

    class Meta:
        verbose_name = 'SagePay Transaction'

    def __unicode__(self):
        return self.vendor_tx_code