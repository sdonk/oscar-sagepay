from django.conf.urls import patterns, url

from .views import SagePayNotificationHandlerView, SagePayCreditCardFormView, SageErrorView, SageThankYouView


urlpatterns = patterns('',
    url(r'notification/$', SagePayNotificationHandlerView.as_view(), name='notification_url'),
    url(r'pay/(?P<tx_id>{(\w{8})-(\w{4})-(\w{4})-(\w{4})-(\w{12})})/$', SagePayCreditCardFormView.as_view(), name='credit_card_form'),
    url(r'error/(?P<error>\d{1})/$', SageErrorView.as_view(), name='error'),
    url(r'thankyou/(?P<tx_id>{(\w{8})-(\w{4})-(\w{4})-(\w{4})-(\w{12})})/$', SageThankYouView.as_view(), name='thankyou')
        )
