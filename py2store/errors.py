class KeyValidationError(ValueError):
    """Error to raise when a key is not valid"""
    pass


class NoSuchKeyError(KeyError):
    pass


class OperationNotAllowed(PermissionError):
    pass


class ReadsNotAllowed(OperationNotAllowed):
    pass


class WritesNotAllowed(OperationNotAllowed):
    pass


class DeletionsNotAllowed(OperationNotAllowed):
    pass


class OverWritesNotAllowedError(OperationNotAllowed):
    """Error to raise when a key is not valid"""
    pass
