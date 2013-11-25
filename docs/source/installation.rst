============
Installation
============

Install the plugin
------------------

.. tip::

    Work in a `virtual environment`_!

1. Install django-oscar-sagepay using pip or clone the repository and use setup.py:

.. code-block:: bash

    pip install oscar-sagepay==1.0

.. code-block:: bash

    git clone https://github.com/sdonk/django-oscar-sagepay.git
    cd oscar-sagepay
    python setup.py install

2. Add "sagepay" to your INSTALLED_APPS setting like this::

      INSTALLED_APPS = (
          ...
          'sagepay',
      )

3. Run south to sync the db

.. code-block:: bash

    ./manage.py migrate sagepay

.. _virtual environment:  http://virtualenvwrapper.readthedocs.org/en/latest/

Load the initial data
---------------------

The plugin needs the CountryCode model table to be prepopulated and Oscar countries **MUST** be imported as well.

The class :class:`sagepay.utils.CountryHelper` provides all the necessary methods to import and sync the countries,
moreover its method *set_shipping_countries* can be used to set the shipping countries.

There are three steps:

1. Populate the :class:`sagepay.models.CountryCode`
2. Sync the :class:`oscar.apps.address.models.Country`
3. Set the shipping countries according to the countries set in the plugin settings.py

Each step has a dedicated method in :class:`sagepay.utils.CountryHelper`, there's a fourth method called lazy_import that
performs all the three steps in the right oder.

.. code-block:: python

    from sagepay.utils import CountryHelper

    country_helper =  CountryHelper()
    country_helper.lazy_import(sage_import=True)
    >>> True


There's a management command as well that can be used:

.. code-block:: bash

    ./manage.py countrysync --sageimport True


Another management command can set the shipping countries according to the countries set in the settings:

.. code-block:: bash

    ./manage.py setshippingcountry


Override Oscar's checkout views
-------------------------------

**views.py:**
.. code-block:: python

    from sagepay.views import PayDetailsView, ThankYouView, ShippingAddressView


    class PaymentDetailsView(PayDetailsView):
        pass

    class ThankYouView(ThankYouView):
        pass

    class ShippingAddressView(ShippingAddressView):
        pass


**app.py:**
.. code-block:: python

    from oscar.apps.checkout.app import CheckoutApplication as CoreCheckoutApplication
    from .views import PaymentDetailsView, ThankYouView, ShippingAddressView

    class CheckoutApplication(CoreCheckoutApplication):
        payment_details_view = PaymentDetailsView
        thankyou_view = ThankYouView
        shipping_address_view = ShippingAddressView

    application = CheckoutApplication()



Override Oscar's customer views
-------------------------------
**app.py**
.. code-block:: python

    from django.conf.urls import patterns, url
    from django.contrib.auth.decorators import login_required

    from oscar.apps.customer.app import CustomerApplication as OscarCustomerApplication
    from sagepay.customer_views import AccountSummaryView, DeleteStoredCardView, OrderLineView

    class CustomerApplication(OscarCustomerApplication):
        summary_view = AccountSummaryView
        credit_card_delete_view = DeleteStoredCardView
        order_line_view = OrderLineView

        def get_urls(self):
            urls = super(CustomerApplication, self).get_urls()
            urls += patterns('',
                    url(r'^cards/(?P<pk>\d+)/delete/$',
                    login_required(self.credit_card_delete_view.as_view()),
                    name='card-delete'),
                             )
            return urls

    application = CustomerApplication()


Update urls.py
--------------

**urls.py**

.. code-block:: python

    urlpatterns += patterns('',
        url(r'^sagepay/', include('sagepay.urls', namespace='sagepay', app_name='sagepay')),
        url(r'^dashboard/sagepay/', include(sagepay_application.urls)),
    )


Dashboard
---------

**settings.py**
.. code-block:: python

    OSCAR_DASHBOARD_NAVIGATION += [
        {
            'label': ('SagePay transactions'),
            'icon': 'icon-money',
            'url_name': 'sagepay-transaction-list'
        },
    ]