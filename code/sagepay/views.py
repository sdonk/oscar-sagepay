########################################################################################################################
# All the views not inheriting from an Oscar one should inherit from CheckoutSessionMixin to handle the session cookie #
########################################################################################################################

import logging

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import TemplateView, View
from django.db.models import get_model


from oscar.core.loading import get_class, get_classes
from oscar.apps.checkout.views import PaymentDetailsView as OscarPaymentDetailsView
from oscar.apps.checkout.views import ThankYouView as OscarThankYouView
from oscar.apps.checkout.views import ShippingAddressView as OscarShippingAddressView
from oscar.apps.checkout.views import CheckoutSessionMixin
from oscar.apps.payment import models

Basket = get_model('basket', 'Basket')


from .facade import Facade
from .forms import BillingAddressForm, ShippingAddressForm
import settings as localsettings

# Standard logger for checkout events
logger = logging.getLogger('oscar.checkout')

pre_payment, post_payment = get_classes('checkout.signals', ['pre_payment', 'post_payment'])
RedirectRequired, UnableToTakePayment, PaymentError = get_classes(
    'payment.exceptions', ['RedirectRequired', 'UnableToTakePayment', 'PaymentError'])
UnableToPlaceOrder = get_class('order.exceptions', 'UnableToPlaceOrder')
CheckoutSessionData = get_class('checkout.utils', 'CheckoutSessionData')
OrderPlacementMixin = get_class('checkout.mixins', 'OrderPlacementMixin')

SAVE_CARD = getattr(localsettings, 'SAGEPAY_SAVE_CARD', False)

class ShippingAddressView(OscarShippingAddressView):
    form_class = ShippingAddressForm

class PayDetailsView(OscarPaymentDetailsView):
    """
    https://django-oscar.readthedocs.org/en/latest/ref/apps/checkout.html?highlight=checkout#oscar.apps.checkout.views
    """
    def __init__(self, *args, **kwargs):
        self.facade = Facade()
        return  super(PayDetailsView, self).__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        # Override method so the billing address form can be added to the context.
        ctx = super(PayDetailsView, self).get_context_data(**kwargs)
        ctx['billing_address_form'] = kwargs.get('billing_address_form', BillingAddressForm())
        ctx['credit_cards'] = self.facade.get_credit_cards(self.request.user)
        ctx['saved_cards'] = SAVE_CARD
        return ctx

    def post(self, request, *args, **kwargs):
        # Override so we can validate the billing address submission. If
        # it is valid, we render the preview screen with the forms hidden within
        # it.  When the preview is submitted, we pick up the 'action' parameters
        # and actually place the order.
        if request.POST.get('action', '') in ('place_order', 'saved_card'):
            return self.do_place_order(request)

        billing_address_form = BillingAddressForm(request.POST)
        # inject token into the billing_address_form so it's carried over the views into the hidden billings form field
        if not billing_address_form.is_valid():
            # Form validation failed, render page again with errors
            self.preview = False
            ctx = self.get_context_data(billing_address_form=billing_address_form)
            return self.render_to_response(ctx)

        # Render preview with bankcard and billing address details hidden
        return self.render_preview(request, billing_address_form=billing_address_form)

    def do_place_order(self, request):
        # Helper method to check that the hidden forms wasn't tinkered
        # with

        # enter this if using a new card
        if request.POST.get('action', '') == 'place_order':
             # check if save credit card details checkbox is ticked
            if 'save_card' in request.POST.dict().keys():
                save_card = True
            else:
                save_card = False
            billing_address_form = BillingAddressForm(request.POST)
            if not billing_address_form.is_valid():
                messages.error(request, "Invalid billing address")
                return HttpResponseRedirect(reverse('checkout:payment-details'))
            # Attempt to submit the order, passing the bankcard object so that it
            # gets passed back to the 'handle_payment' method below.
            return self.submit(
                request.basket,
                payment_kwargs={
                    'billing_address': billing_address_form.cleaned_data,
                    'shipping_address':  self.get_shipping_address(),
                    'save_card': save_card,
                    })
        # enter this if using a stored credit card
        elif request.POST.get('action', '') == 'saved_card':
            card_token = request.POST.get('token', '')
            if card_token == '':
                messages.error(request, "Invalid saved card")
                return  HttpResponseRedirect(reverse('checkout:payment-details'))
            # Attempt to submit the order, passing the bankcard object so that it
            # gets passed back to the 'handle_payment' method below.
            return self.submit(
                request.basket,
                payment_kwargs={
                    'shipping_address':  self.get_shipping_address(),
                    'card_token': card_token,
                    })

    def submit(self, basket, payment_kwargs=None, order_kwargs=None):
        """
        Submit a basket for order placement.

        The process runs as follows:
         * Generate an order number
         * Freeze the basket so it cannot be modified any more (important when
           redirecting the user to another site for payment as it prevents the
           basket being manipulated during the payment process).
         * Attempt to take payment for the order
           - If payment is successful, place the order
           - If a redirect is required (eg PayPal, 3DSecure), redirect
           - If payment is unsuccessful, show an appropriate error message

        :basket: The basket to submit.
        :payment_kwargs: Additional kwargs to pass to the handle_payment method.
        :order_kwargs: Additional kwargs to pass to the place_order method.

        https://github.com/tangentlabs/django-oscar/blob/0.5.1/oscar/apps/checkout/views.py
        """
        if payment_kwargs is None:
            payment_kwargs = {}
        if order_kwargs is None:
            order_kwargs = {}

        # Next, check that basket isn't empty
        if basket.is_empty:
            messages.error(self.request, ("This order cannot be submitted as the basket is empty"))
            url = self.request.META.get('HTTP_REFERER', reverse('basket:summary'))
            return HttpResponseRedirect(url)

        # Domain-specific checks on the basket
        is_valid, reason, url = self.can_basket_be_submitted(basket)
        if not is_valid:
            messages.error(self.request, reason)
            return HttpResponseRedirect(url)

        # We generate the order number first as this will be used
        # in payment requests (ie before the order model has been
        # created).  We also save it in the session for multi-stage
        # checkouts (eg where we redirect to a 3rd party site and place
        # the order on a different request).
        order_number = self.generate_order_number(basket)
        logger.info("Order #%s: beginning submission process for basket #%d", order_number, basket.id)

        # Freeze the basket so it cannot be manipulated while the customer is
        # completing payment on a 3rd party site.  Also, store a reference to
        # the basket in the session so that we know which basket to thaw if we
        # get an unsuccessful payment response when redirecting to a 3rd party
        # site.
        self.freeze_basket(basket)
        self.checkout_session.set_submitted_basket(basket)

        # Handle payment.  Any payment problems should be handled by the
        # handle_payment method raise an exception, which should be caught
        # within handle_POST and the appropriate forms redisplayed.
        error_msg = ("A problem occurred while processing payment for this "
                      "order - no payment has been taken.  Please "
                      "contact customer services if this problem persists")
        pre_payment.send_robust(sender=self, view=self)
        total_incl_tax, total_excl_tax = self.get_order_totals(basket)
        try:
            return self.handle_payment(order_number, basket, total_incl_tax, **payment_kwargs)
        except RedirectRequired, e:
         #   Redirect required (eg PayPal, 3DS)
            logger.info("Order #%s: redirecting to %s", order_number, e.url)
            return HttpResponseRedirect(e.url)
        except UnableToTakePayment, e:
            # Something went wrong with payment but in an anticipated way.  Eg
            # their bankcard has expired, wrong card number - that kind of
            # thing. This type of exception is supposed to set a friendly error
            # message that makes sense to the customer.
            msg = unicode(e)
            logger.warning("Order #%s: unable to take payment (%s) - restoring basket", order_number, msg)
            self.restore_frozen_basket()
            return self.render_to_response(self.get_context_data(error=msg))
        except PaymentError, e:
            # A general payment error - Something went wrong which wasn't
            # anticipated.  Eg, the payment gateway is down (it happens), your
            # credentials are wrong - that king of thing.
            # It makes sense to configure the checkout logger to
            # mail admins on an error as this issue warrants some further
            # investigation.
            msg = unicode(e)
            logger.error("Order #%s: payment error (%s)", order_number, msg)
            self.restore_frozen_basket()
            return self.render_to_response(self.get_context_data(error=error_msg))
        except Exception, e:
            # Unhandled exception - hopefully, you will only ever see this in
            # development.
            logger.error("Order #%s: unhandled exception while taking payment (%s)", order_number, e)
            logger.exception(e)
            self.restore_frozen_basket()
            return self.render_to_response(self.get_context_data(error=error_msg))
        post_payment.send_robust(sender=self, view=self)

    def handle_payment(self, order_number, basket, amount, **kwargs):
        # Make submission to SagePay, this is where the fun starts.
        shipping_address = kwargs['shipping_address']
        if 'card_token' in kwargs:
            tx_id = self.facade.authorize(order_number, basket, amount, shipping_address, card_token=kwargs['card_token'])
        else:
            billing_address = kwargs['billing_address']
            tx_id = self.facade.authorize(order_number, basket, amount, shipping_address, billing_address=billing_address, save_card=kwargs['save_card'])

        url = reverse('sagepay:credit_card_form', kwargs={'tx_id': tx_id})
        return HttpResponseRedirect(url)


class SagePayCreditCardFormView(CheckoutSessionMixin, TemplateView):
    """
    Renders the credit card form into an iframe
    """
    template_name = "checkout/sage_card.html"

    def get_context_data(self, **kwargs):
        context = super(SagePayCreditCardFormView, self).get_context_data(**kwargs)
        context['tx_id'] = self.kwargs['tx_id']
        return context


class SagePayNotificationHandlerView(CheckoutSessionMixin, View):
    """
    This views handles the SagePay response to the payment registration POST (Step 3 and 9 on the Sage guide) and
    it's passed to the SagePay server into the NotificationURL flag
    Plus it saves the payment into oscar if everything is ok
    It doesn't act as a view (i.e. it's not displayed to the user in the frontend) but it can be attached to a URL!
    """
    def post(self, request, *args, **kwargs):
        facade = Facade()
        response = facade.check_transaction_notification(request.POST.dict())
        return HttpResponse(response, content_type='text/plain')

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SagePayNotificationHandlerView, self).dispatch(request, *args, **kwargs)


class SageThankYouView(OrderPlacementMixin, View):
    """
    Handle the basket/order using the oscar mixin

    'Override this view if you want to perform custom actions when an
    order is submitted.' from:
    https://github.com/tangentlabs/django-oscar/blob/0.5.1/oscar/apps/checkout/mixins.py
    """
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.checkout_session = CheckoutSessionData(self.request)
        tx_id = kwargs['tx_id']
        facade = Facade()
        order_id, basket, amount = facade.order_basket_amount_from_tx_id(tx_id)
        super(SageThankYouView, self).dispatch(request, *args, **kwargs)
        return self.finalise(order_id, basket, amount)

    def finalise(self, order_id, basket_id, amount):
        order_number = order_id
        basket = basket_id
        total_incl_tax = amount
        total_excl_tax = total_incl_tax
        order_kwargs = {}
        # Record payment source and event
        source_type, is_created = models.SourceType.objects.get_or_create(name='SagePay')
        source = models.Source(source_type=source_type,
                               currency='GBP',
                               amount_allocated=total_incl_tax)
        self.add_payment_source(source)
        self.add_payment_event('Authorised', total_incl_tax)
        # finalising the order into oscar
        logger.info("Order #%s: payment successful, placing order", order_number)
        try:
            return self.handle_order_placement(order_number, basket,
                                               total_incl_tax, total_excl_tax,
                                               **order_kwargs)
        except UnableToPlaceOrder, e:
            # It's possible that something will go wrong while trying to
            # actually place an order.  Not a good situation to be in, but needs
            # to be handled gracefully.
            logger.error("Order #%s: unable to place order - %s", order_number, e)
            msg = unicode(e)
            self.restore_frozen_basket()
            return self.render_to_response(self.get_context_data(error=msg))

class SageErrorView(CheckoutSessionMixin, View):
    """
    Redirect the user to the basket showing the right message using the Oscar (django) message system
    """
    errors = {
        '1': 'Not Authorized: please check your details',
        '2': 'Abort: transaction cancelled',
        '3': 'Rejected: transaction rejected because of the fraud screening rules'
    }

    def dispatch(self, request, *args, **kwargs):
        if kwargs['error'] == '1':
            messages.error(request, "Transaction not authorized, please check your details")
            return HttpResponseRedirect(reverse('basket:summary'))
        elif kwargs['error'] == '2':
            messages.error(request, "Transaction cancelled")
            return HttpResponseRedirect(reverse('basket:summary'))
        elif kwargs['error'] == '3':
            messages.error(request, "Transaction has been rejected because of the fraud screening rules")
            return HttpResponseRedirect(reverse('basket:summary'))

class ThankYouView(OscarThankYouView):
    """
    Need to use a custom template to break out of the iframe
    """
    template_name = "checkout/thank_you.html"

    def dispatch(self, request, *args, **kwargs):
        return super(ThankYouView, self).dispatch(request, *args, **kwargs)

    def get_object(self):
        obj = super(ThankYouView, self).get_object()
        self.save_billing_address(obj)
        return obj

    def save_billing_address(self, order):
        facade = Facade()
        facade.save_billing_address_from_order(order)
