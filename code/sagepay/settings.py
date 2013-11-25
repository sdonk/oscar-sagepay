from django.conf import settings
from django.contrib.sites.models import Site

site = Site.objects.get_current()
domain = site.domain

# set constant settings
if settings.DEBUG :
    SAGE_SERVER_URL = getattr(settings, 'SAGEPAY_SERVER', 'https://test.sagepay.com/gateway/service/vspserver-register.vsp')
    DELETE_TOKEN_URL = getattr(settings, 'SAGEPAY_DELETETOKEN', 'https://test.sagepay.com/gateway/service/removetoken.vsp')
    NOTIFICATION_URL = getattr(settings, 'SAGEPAY_NOTIFICATION_URL', 'http://%s/sagepay/notification/' % domain)
    THANK_YOU_URL = getattr(settings, 'SAGEPAY_THANK_YOU_URL', 'http://%s/sagepay/thankyou/' % domain)
    ERROR_URL = getattr(settings, 'SAGEPAY_ERROR_URL', 'http://%s/sagepay/error/' % domain)
else:
    SAGE_SERVER_URL = getattr(settings, 'SAGEPAY_SERVER', 'https://live.sagepay.com/gateway/service/vspserver-register.vsp')
    DELETE_TOKEN_URL = getattr(settings, 'SAGEPAY_DELETETOKEN', 'https://live.sagepay.com/gateway/service/removetoken.vsp')
    NOTIFICATION_URL = getattr(settings, 'SAGEPAY_NOTIFICATION_URL', 'http://%s/sagepay/notification/' % domain)
    THANK_YOU_URL = getattr(settings, 'SAGEPAY_THANK_YOU_URL', 'http://%s/sagepay/thankyou/' % domain)
    ERROR_URL = getattr(settings, 'SAGEPAY_ERROR_URL', 'http://%s/sagepay/error/' % domain)


SAGEPAY_PROFILE = getattr(settings, 'SAGEPAY_PROFILE', 'LOW')
VENDOR = getattr(settings, 'SAGEPAY_VENDOR', '')
PROTOCOL = getattr(settings, 'SAGEPAY_VPSPROTOCOL', '3.00')
DEFAULT_CURRENCY = getattr(settings, 'SAGEPAY_DEFAULT_CURRENCY', 'GBP')
SAVE_CARD = getattr(settings, 'SAGEPAY_SAVE_CARD', False)
