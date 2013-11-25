========
Settings
========

The following settings can be set in the main settings Django file, default value is used if nothing provided:

``SAGEPAY_VPSPROTOCOL``
-----------------------

Default live: ``'3.00'``

Default test: ``'3.00'``

The SagePay server protocol number, it doesn't need to be changed.

``SAGEPAY_PROFILE``
-------------------

Default live: ``'LOW'``

Default test: ``'LOW'``

LOW actives the iframe version, switch to NORMAL if you don't want to use iframe (not supported yet).

``SAGEPAY_VENDOR``
------------------

The vendor name used to login into SagePay, this **MUST** be defined

``SAGEPAY_SAVE_CARD``
---------------------

Default live: ``FALSE``

Default test: ``FALSE``

Flag to set the save credit card feature

``SAGEPAY_DEFAULT_CURRENCY``
----------------------------

Default live: ``'GBP'``

Default test: ``'GBP'``

``SAGEPAY_SERVER``
------------------

Default live: ``'https://test.sagepay.com/gateway/service/vspserver-register.vsp'``

Default test: ``'https://live.sagepay.com/gateway/service/vspserver-register.vsp'``

The SagePay server URL, it doesn't need to be changed.


``SHIPPING_COUNTRIES``
----------------------

Default live: ``('United Kingdom',)``

Default test: ``('United Kingdom',)``

Not really a SagePay setting as it sets the is_shipping flag to True oscar country model.

.. warning::
    It **MUST** be a list of strings matching the imported SagePay countries.