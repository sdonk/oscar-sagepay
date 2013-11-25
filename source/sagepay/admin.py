from django.contrib import admin
from django.conf import settings

from .models import SagePayTransaction, TransactionRegistrationServerResponse, CountryCode, NotificationPostResponse, Token


class SagePayTransactionAdmin(admin.ModelAdmin):
    readonly_fields = ('vendor_tx_code', 'transaction_registration_server_response', 'notification_post_response', 'token')
    list_display = ('vendor_tx_code', 'tx_type', 'amount', 'transaction_registration_server_response', 'notification_post_response', 'created')


class TransactionRegistrationServerResponseAdmin(admin.ModelAdmin):
    list_display = ('vps_tx_id', 'status','security_key', 'created')


class NotificationPostResponseAdmin(admin.ModelAdmin):
    list_display = ('vps_tx_id', 'status', 'tx_auth_no', 'bank_auth_ode', 'created')

if settings.DEBUG:
    admin.site.register(SagePayTransaction, SagePayTransactionAdmin)
    admin.site.register(TransactionRegistrationServerResponse, TransactionRegistrationServerResponseAdmin)
    admin.site.register(NotificationPostResponse, NotificationPostResponseAdmin)
    admin.site.register(CountryCode)
    admin.site.register(Token)
