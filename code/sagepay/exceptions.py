# gateway exceptions
class GatewayException(Exception):
    pass

# facade exceptions
class NotApproved(Exception):
    pass

class Abort(Exception):
    pass

class Rejected(Exception):
    pass

class TransactionDoesNotExistException(Exception):
    pass