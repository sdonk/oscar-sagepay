from optparse import make_option

from django.core.management.base import  BaseCommand, CommandError

from sagepay.utils import CountryHelper

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--sageimport',
                    action='store_true',
                    dest='import',
                    default=False,
                    help='Fetch and import the countries in the SagePay CountryCode model'),
    )
    help = 'Syncronize the countries models (sagepay->oscar) and set the shipping countries. SagePay must be already imported, if not use --sageimport=True'

    def handle(self, *args, **options):
        c = CountryHelper()
        if options['import']:
            try:
                c.lazy_import(populate_sage=True)
            except Exception, e:
                raise CommandError(e)
        else:
            try:
                c.lazy_import(populate_sage=False)
            except Exception, e:
                raise CommandError(e)

