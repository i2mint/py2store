from functools import partial
import json
import marshal


def mk_marshal_rw_funcs(**kwargs):  # TODO: Check actual arguments for marshal load and dump
    """Generates a reader and writer using marshal. That is, a pair of parametrized loads and dumps

    >>> read, write = mk_marshal_rw_funcs()
    >>> d = {'a': 'simple', 'and': {'a': b'more', 'complex': [1, 2.2, dict]}}
    >>> serialized_d = write(d)
    >>> deserialized_d = read(serialized_d)
    >>> assert d == deserialized_d
    """
    return partial(marshal.dumps, **kwargs)
