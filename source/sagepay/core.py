class TransactionNotificationPostResponse(object):
    """
    Encapsulate the notification of results of transactions into an object
    (page 63 of sage manual)

    :param response: content of the SagePay server notification post
    :type response: dictionary
    """
    def __init__(self, response):
        self.response = response

    def __getitem__(self, key):
        return self.response[key]

    def __contains__(self, key):
        return key in self.response

    def get(self, key, default):
        """
        Return the  corresponding value to the key or default if the key is not found

        :param key: key to lookup
        :type key: str
        :param default: default value to return
        :type default: everything
        :returns: dictionary value or default
        """
        try:
            return self.response[key]
        except KeyError:
            return default

    def post_format(self, vendor_name, security_key):
        """
        Reconstruct the POST response content to be MD5 hashed and matched for preventing tampering

        :param vendor_name: SagePay vendor name
        :type vendor_name: str
        :param security_key: security key saved associated to the transaction
        :type security_key: :class:`sagepay.models.SagePayTransaction` security key field
        :returns: str
        """
        values = (
            self.response.get('VPSTxId', ''),
            self.response.get('VendorTxCode', ''),
            self.response.get('Status', ''),
            self.response.get('TxAuthNo', ''),
            vendor_name,
            self.response.get('AVSCV2', ''),
            security_key.strip(),
            self.response.get('AddressResult', ''),
            self.response.get('PostCodeResult', ''),
            self.response.get('CV2Result', ''),
            self.response.get('GiftAid', ''),
            self.response.get('3DSecureStatus', ''),
            self.response.get('CAVV', ''),
            #self.response.get('AddressStatus', ''),
            #self.response.get('PayerStatus', ''),
            self.response.get('CardType', ''),
            self.response.get('Last4Digits', ''),
            self.response.get('DeclineCode', ''),
            self.response.get('ExpiryDate', ''),
            #self.response.get('FraudResponse', ''),
            self.response.get('BankAuthCode', ''),
        )
        return ''.join(values)

    @property
    def ok(self):
        """
        True if the transaction status is ok
        """
        if self.response['Status'] == 'OK':
            return True
        else:
            return False

    @property
    def pending(self):
        """
        True if the transaction status is pending
        """
        if self.response['Status'] == 'PENDING':
            return True
        else:
            return False

    @property
    def notauthed(self):
        """
        True if the transaction status is notauthed
        """
        if self.response['Status'] == 'NOTAUTHED':
            return True
        else:
            return False

    @property
    def abort(self):
        """
        True if the transaction status is abort
        """
        if self.response['Status'] == 'ABORT':
            return True
        else:
            return False

    @property
    def rejected(self):
        if self.response['Status'] == 'REJECTED':
            return True
        else:
            return False

    @property
    def authenticated(self):
        """
        True if the transaction status is authenticated
        """
        if self.response['Status'] == 'AUTHENTICATED':
            return True
        else:
            return False

    @property
    def registered(self):
        """
        True if the transaction status is registered
        """
        if self.response['Status'] == 'REGISTERED':
            return True
        else:
            return False

    @property
    def error(self):
        """
        True if the transaction status is error
        """
        if self.response['Status'] == 'ERROR':
            return True
        else:
            return False


class Response(object):
    """
    Encapsulate SagePay response into a Python object

    :param response: :class:`requests.Response` instance
    """
    def __init__(self, response):
        self.response = response
        self.data = self._convert_data(response)

    def _convert_data(self, response):
        sage_response = {}
        for i in response.split('\n'):
            line = i.split('=')
            if 'NextURL' in line[0]:
                sage_response[line[0]] = '%s=%s' % (line[1].strip(), line[2].strip())
            else:
                sage_response[line[0]] = line[1].strip()
        return sage_response

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.response

    @property
    def is_successful(self):
        """
        Check if the status of the response is OK

        :returns: Boolean
        """
        if 'OK' in self.data['Status']:
            return True
        else:
            return False
