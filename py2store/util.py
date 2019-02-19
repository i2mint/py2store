class lazyprop:
    """
    A descriptor implementation of lazyprop (cached property) from David Beazley's "Python Cookbook" book.
    It's
    >>> class Test:
    ...     def __init__(self, a):
    ...         self.a = a
    ...     @lazyprop
    ...     def len(self):
    ...         print('generating "len"')
    ...         return len(self.a)
    >>> t = Test([0, 1, 2, 3, 4])
    >>> t.__dict__
    {'a': [0, 1, 2, 3, 4]}
    >>> t.len
    generating "len"
    5
    >>> t.__dict__
    {'a': [0, 1, 2, 3, 4], 'len': 5}
    >>> t.len
    5
    >>> # But careful when using lazyprop that no one will change the value of a without deleting the property first
    >>> t.a = [0, 1, 2]  # if we change a...
    >>> t.len  # ... we still get the old cached value of len
    5
    >>> del t.len  # if we delete the len prop
    >>> t.len  # ... then len being recomputed again
    generating "len"
    3
    """

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = self.func(instance)
            setattr(instance, self.func.__name__, value)
            return value
