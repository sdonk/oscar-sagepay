from django.views.generic import DeleteView
from django.core.urlresolvers import reverse_lazy, reverse
from django.conf import settings
from django.http import HttpResponseRedirect, Http404
from django.contrib import messages
from django.db.models import get_model
from django.shortcuts import get_object_or_404

from oscar.apps.customer.views import AccountSummaryView as OscarAccountSummaryView
from oscar.apps.customer.views import OrderLineView as OscarOrderLineView

from .models import Token

SAVE_CARD = getattr(settings, 'SAGEPAY_SAVE_CARD', False)

Order = get_model('order', 'Order')

class AccountSummaryView(OscarAccountSummaryView):
    def get_context_data(self, **kwargs):
        ctx = super(AccountSummaryView, self).get_context_data(**kwargs)
        ctx['saved_cards'] = SAVE_CARD
        ctx['credit_cards'] = self.get_credit_cards(self.request.user)
        return ctx

    def get_credit_cards(self, user):
        return Token.objects.filter(user=user)

class DeleteStoredCardView(DeleteView):
    #model = Token
    template_name = 'customer/card_delete.html'

    def get_queryset(self):
        return Token.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse('customer:summary')

class OrderLineView(OscarOrderLineView):
    """Customer order line"""

    def get_object(self, queryset=None):
        """Return an order object or 404"""
        order = get_object_or_404(Order, user=self.request.user,
                                  number=self.kwargs['order_number'])
        return order.lines.get(id=self.kwargs['line_id'])

    def do_reorder(self, line):
        self.response = HttpResponseRedirect(reverse('customer:order',
                                    args=(int(self.kwargs['order_number']),)))
        basket = self.request.basket

        line_available_to_reorder, reason = line.is_available_to_reorder(basket,
            self.request.user)

        if not line_available_to_reorder:
            messages.warning(self.request, reason)
            return

        # We need to pass response to the get_or_create... method
        # as a new basket might need to be created
        self.response = HttpResponseRedirect(reverse('basket:summary'))

        # Convert line attributes into basket options
        options = []
        for attribute in line.attributes.all():
            if attribute.option:
                options.append({'option': attribute.option, 'value': attribute.value})
        basket.add_product(line.product, line.quantity, options)

        if line.quantity > 1:
            msg = ("%(qty)d copies of '%(product)s' have been added to your basket") % {
                'qty': line.quantity, 'product': line.product}
        else:
            msg = ("'%s (%s)' has been added to your basket") % (line.product, line.track_format)

        messages.info(self.request, msg)