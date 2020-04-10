from collections.abc import Mapping


def items_with_caught_exceptions(d: Mapping, callback=None, catch_exceptions=(KeyError,)):
    """
    Do what Mapping.items() does, but catching exceptions when getting the values for a key.

    :param d: Any Mapping
    :param catch_exceptions: A tuple of exceptions that should be caught
    :param callback: A function that will be called on the key and exception object every time an exception is caught
    :return: An (key,val) generator with exceptions caught

    >>> from collections.abc import Mapping
    >>> class Test(Mapping):  # a Mapping class that has keys 0..9, but raises of KeyError if the key is not even
    ...     n = 10
    ...     def __iter__(self):
    ...         yield from range(self.n)
    ...     def __len__(self):
    ...         return self.n
    ...     def __getitem__(self, k):
    ...         if k % 2 == 0:
    ...             return k
    ...         else:
    ...             raise KeyError('Not even')
    >>>
    >>> list(items_with_caught_exceptions(Test()))
    [(0, 0), (2, 2), (4, 4), (6, 6), (8, 8)]
    >>> list(items_with_caught_exceptions(Test(), callback=print))
    1 'Not even'
    3 'Not even'
    5 'Not even'
    7 'Not even'
    9 'Not even'
    [(0, 0), (2, 2), (4, 4), (6, 6), (8, 8)]
    """
    for k in d:
        try:
            v = d[k]
            yield k, v
        except catch_exceptions as e:
            if callback is not None:
                callback(k, e)


def _assert_condition(condition, err_msg='', err_cls=AssertionError):
    if not condition:
        raise err_cls(err_msg)


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
