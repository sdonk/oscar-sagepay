from django.db.models import get_model
from django.conf import settings

import requests

from .models import SagePayTransaction, CountryCode
from .gateway import Gateway
from .models import CountryCode

Basket = get_model('basket', 'Basket')
Order = Basket = get_model('order', 'order')
Country = get_model('address', 'Country')

SHIPPING_COUNTRIES = getattr(settings, 'SHIPPING_COUNTRIES', ['United Kingdom',])
SHIPPING_COUNTRIES = [country.title() for country in SHIPPING_COUNTRIES]

class CountryHelper(object):

    def populate_sagepay_country_code(self):
        """
        Import the country codes from
        http://www.iso.org/iso/home/standards/country_codes/country_names_and_code_elements_txt.htm

        :returns: boolean - state of import
        """
        try:
            r = requests.get('http://www.iso.org/iso/home/standards/country_codes/country_names_and_code_elements_txt.htm')
        except requests.RequestException:
            return False
        countries = r.text.split('\r\n')
        for country in countries[1:-2]:
            country = country.split(';')
            try:
                c = CountryCode(name=country[0].capitalize(), code=country[1])
                c.save()
            except: #todo don't catch all the exceptions, this is just temporary
                return False
        return True

    def sync_country_models(self):
        """
        Sync :class:`sagepay.models.CountryCode` and :class:`oscar.apps.address.models.Country`
        this function has to run after :func:`populate_country_code` has been executed

        :returns: boolean - state of import
        """
        country_list = []
        for country in CountryCode.objects.all():
            c = Country(iso_3166_1_a2=country.code,
                        iso_3166_1_a3=country.code,
                        iso_3166_1_numeric=1,
                        name=country.name.upper(),
                        printable_name=country.name.title(),
                        is_shipping_country=False)
            country_list.append(c)
        try:
            Country.objects.bulk_create(country_list)
            return True
        except:
            return False

    def set_shipping_countries(self):
        """
        Set the shipping countries according to the SHIPPING_COUNTRIES parameter

        :returns: boolean - state of import
        """
        Country.objects.filter(printable_name__in=SHIPPING_COUNTRIES).update(is_shipping_country=True)

    def lazy_import(self, populate_sage=True):
        """
        This method is a lazy helper to run the three steps:

        1. fetch and populate :class:`sagepay.models.CountryCode`
        2. Sync the :class:`oscar.apps.address.models.Country`
        3. Set the shipping countries

        :param populate_sage: if false skips the step 1, useful if the object are imported in SagePay using the Django
        fixtures
        :type populate_sage: bool

        """
        if populate_sage:
            self.populate_sagepay_country_code()
        self.sync_country_models()
        self.set_shipping_countries()



def utf8_truncate(s, max_length):
    """
    Truncate a unicode string so that its UTF-8 representation will not be longer
    than `max_length` bytes

    Hat tip: http://stackoverflow.com/questions/1809531/

    :param s: string to be truncated
    :type s: str
    :param max_length: length to truncate to
    :type max_length: int
    """
    encoded = s.encode('utf-8')
    # The 'ignore' flag ensures that if a multibyte char gets chopped halfway it
    # will just be dropped
    return encoded[:max_length].decode('utf-8', 'ignore')

# functions util for testing purpose
def add_fake_transaction():
    """
    Add a fake transaction to the database to simulate the credit card form

    :returns: instance - :class:`sagepay.models.SagePayTransaction`
    """
    uk = CountryCode.objects.get(code='GB')
    basket = Basket.object.get(id=1)
    order =  Order.object.get(id=1)
    t = SagePayTransaction(
        amount=10,
        oscar_basket = basket,
        oscar_order = order,
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
    t.save()
    return t

def set_test_gateway():
    """
    Initialise a gateway class with test SagePay server set as URL

    :returns: :class:`sagepay.gateway.Gateway`
    """
    g = Gateway('LOW','http://fdsfdsfdsf.com','https://test.sagepay.com/gateway/service/vspserver-register.vsp')
    return g
