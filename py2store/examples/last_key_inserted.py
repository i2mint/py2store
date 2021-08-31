"""
showing how to add the knowledge of the 'last key inserted' to stores
"""
from functools import wraps, partial

NoKeyWasWrittenToYet = type('NoKeyWasWrittenToYet', (), {})()


def remember_last_key_written_to(
    cls=None, *, only_if_new_key=False, name=None, same_name_as_class=False
):
    """A decorator to get a class that remembers the last key that was written to.
    Note that this is the last key that THIS STORE wrote to, not the last key that was
    written to the DB.

    Some would say "it's not thread-safe", but that statement might be overkill.
    See the code to see what you should or should not expect.

    :param cls: The class you want to decorate (omit if you want to make a decorator factory instead)
    :param only_if_new_key: If by "last written to" we mean "last created"
        (i.e. only keep track if the key is NEW, not if we just updated the value)
    :param name: The name you want the decorated class to have
    :param same_name_as_class: If you want to use the name of the decorated class itself.

    :return: A decorated class (if the class was given), or a class decorator (if cls=None).

    >>> def test(s):
    ...     # test:
    ...     s['hello'] = 'you'
    ...     assert s._last_key_written_to == 'hello'
    ...     s['goodbye'] = 'them'
    ...     assert s._last_key_written_to == 'goodbye'
    ...     s['hello'] = 'you'
    ...     assert s._last_key_written_to == 'hello'
    ...
    >>>
    >>> S = remember_last_key_written_to(dict)
    >>> s = S()
    >>> test(s)
    >>>
    >>> # Use as decorator factory
    >>> @remember_last_key_written_to
    ... class SS(dict):
    ...     pass
    ...
    >>>
    >>> ss = SS()
    >>> test(ss)
    >>>
    >>> SSS = remember_last_key_written_to(dict, only_if_new_key=True)
    >>> sss = SSS()
    >>> assert sss._last_key_written_to is None
    >>> sss['hi'] = 'there'
    >>> sss._last_key_written_to
    'hi'
    >>> sss[3] = .1415
    >>> sss._last_key_written_to
    3
    >>> sss['hi'] = 'this key already exists!'
    >>> sss._last_key_written_to  # so this should still be 3
    3
    """
    if cls is None:
        return partial(remember_last_key_written_to, name=name, same_name_as_class=True)
    else:

        class S(cls):
            @wraps(cls.__init__)
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._last_key_written_to = None

            if only_if_new_key:

                def __setitem__(self, k, v):
                    if k not in self:
                        self._last_key_written_to = k
                    return super().__setitem__(k, v)

            else:

                def __setitem__(self, k, v):
                    self._last_key_written_to = k
                    return super().__setitem__(k, v)

        if name is not None:
            S.__name__ = name
        elif same_name_as_class:
            S.__name__ = cls.__name__

        return S
