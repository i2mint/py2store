class KeyValidationError(ValueError):
    """Error to raise when a key is not valid"""
    pass


class NoSuchKeyError(KeyError):
    pass


class OperationNotAllowed(NotImplementedError):
    pass


class ReadsNotAllowed(OperationNotAllowed):
    pass


class WritesNotAllowed(OperationNotAllowed):
    pass


class DeletionsNotAllowed(OperationNotAllowed):
    pass


class IterationNotAllowed(OperationNotAllowed):
    pass


class OverWritesNotAllowedError(OperationNotAllowed):
    """Error to raise when a key is not valid"""
    pass
