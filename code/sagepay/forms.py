from django import forms
from django.db.models import get_model
from django.conf import settings

SAVE_CARD = getattr(settings, 'SAGEPAY_SAVE_CARD', False)

from oscar.apps.payment.forms import AbstractAddressForm


Country = get_model('address', 'Country')
BillingAddress = get_model('order', 'BillingAddress')


class BillingAddressForm(AbstractAddressForm):

    def __init__(self, *args, **kwargs):
        super(BillingAddressForm,self ).__init__(*args, **kwargs)

        self.fields['line4'].required = True
        self.set_country_queryset()
         # inject the save credit card detail checkbox into the billing address form
        if SAVE_CARD:
            self.fields['save_card'] = forms.BooleanField(label='Save credit card details for future use', required=False)

    def set_country_queryset(self):
        self.fields['country'].queryset = Country._default_manager.all()

    class Meta:
        model = BillingAddress
        exclude = ('search_text',)


class ShippingAddressForm(AbstractAddressForm):

    def __init__(self, *args, **kwargs):
        super(ShippingAddressForm,self ).__init__(*args, **kwargs)
        # sage requires the city in the shipping address
        self.fields['line4'].required = True
        self.set_country_queryset()

    def set_country_queryset(self):
        self.fields['country'].queryset = get_model('address', 'country')._default_manager.filter(
            is_shipping_country=True)

    class Meta:
        model = get_model('order', 'shippingaddress')
        exclude = ('user', 'search_text')