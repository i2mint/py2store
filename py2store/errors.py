class KeyValidationError(ValueError):
    """Error to raise when a key is not valid"""
    pass


class OverWritesNotAllowedError(PermissionError):
    """Error to raise when a key is not valid"""
    pass
