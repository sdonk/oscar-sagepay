import logging

from django.core.urlresolvers import reverse
from django.db.models import get_model
from django.contrib.sites.models import Site

from oscar.apps.checkout.mixins import OrderPlacementMixin as OscarOrderPlacementMixin
from oscar.apps.customer.utils import Dispatcher

CommunicationEventType = get_model('customer', 'CommunicationEventType')
CommunicationEvent = get_model('order', 'CommunicationEvent')

# Standard logger for checkout events
logger = logging.getLogger('oscar.checkout')

class OrderPlacementMixin(OscarOrderPlacementMixin):
    """
    Override https://github.com/tangentlabs/django-oscar/blob/0.5.1/oscar/apps/checkout/mixins.py
    to include the order link into the

    """

    def send_confirmation_message(self, order, **kwargs):
        code = self.communication_type_code
        ctx = {'order': order,
               'lines': order.lines.all()}

        if not self.request.user.is_authenticated():
            path = reverse('customer:anon-order',
                           kwargs={'order_number': order.number,
                                   'hash': order.verification_hash()})
        else:
            path = reverse('customer:order', kwargs={'order_number': order.number})

        site = Site.objects.get_current()
        ctx['status_url'] = 'http://%s%s' % (site.domain, path)
        try:
            event_type = CommunicationEventType.objects.get(code=code)
        except CommunicationEventType.DoesNotExist:
            # No event-type in database, attempt to find templates for this
            # type and render them immediately to get the messages.  Since we
            # have not CommunicationEventType to link to, we can't create a
            # CommunicationEvent instance.
            messages = CommunicationEventType.objects.get_and_render(code, ctx)
            event_type = None
        else:
            # Create CommunicationEvent
            CommunicationEvent._default_manager.create(
                order=order, event_type=event_type)
            messages = event_type.get_messages(ctx)

        if messages and messages['body']:
            logger.info("Order #%s - sending %s messages", order.number, code)
            dispatcher = Dispatcher(logger)
            dispatcher.dispatch_order_messages(order, messages,
                                               event_type, **kwargs)
        else:
            logger.warning("Order #%s - no %s communication event type",
                           order.number, code)