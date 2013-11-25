from django.core.management.base import  BaseCommand, CommandError

from sagepay.utils import CountryHelper

class Command(BaseCommand):
    help = 'Set the shipping countries'

    def handle(self, *args, **options):
        c = CountryHelper()
        c.set_shipping_countries()
