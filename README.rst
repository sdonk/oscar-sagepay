========================
Oscar SagePay 0.1
========================

This packages provides integration between `Django Oscar`_ and `SagePay server inframe integration`_.

At the current version it's possible to complete a transaction and securely save credit cards details for future use:

.. image:: http://i.imgur.com/GANFvgY.png
    :alt: Inframe credit card form
    :align: center

.. image:: http://i.imgur.com/w9jOLr3.png
    :alt: Saved cards in the customer account page
    :align: center


It provides a new dashboard entry as well, to list all the transactions:

.. image: http://i.imgur.com/PYE0Swg.png
    :alt: Transactions admin dashboard
    :align: center

License
-------

This package is release under the GPLv3 license.


Installation
------------

`Detailed documentation`_


Changelog
---------

0.1
~~~
* Include support for payment
* Save customer's credit card details
* Oscar dashboard app


ToDo
----

- Add more tests
- Add localization support



.. _Django Oscar: http://oscarcommerce.com/
.. _SagePay server inframe integration: http://www.sagepay.co.uk/support/find-an-integration-document/server-inframe-integration-documents
.. _Detailed documentation: http://oscar-sagepay.readthedocs.org/en/latest/