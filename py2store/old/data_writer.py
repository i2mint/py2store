from collections.abc import MutableMapping
from py2store.old.obj_source import DictObjSource


class DataWriter(MutableMapping):
    """
    Interface for an DataWriter.
    An DataWriter offers the basic methods: __getitem__, __len__ and __iter__, along with the consequential
    mixin methods that collections.abc.Mapping adds automatically:
        __contains__, keys, items, values, get, __eq__, and __ne__
    (see https://docs.python.org/3/library/collections.abc.html)

    """

    def __setitem__(self, k, v):
        raise NotImplementedError("Need to implement in concrete class")

    def __delitem__(self, k):
        raise NotImplementedError("Need to implement in concrete class")

    def clear(self):
        print('''
        The MutableMapping clear method was overridden to make dangerous difficult.
        If you really want to delete all your data, you can do so by doing:
            try:
                while True:
                    self.popitem()
            except KeyError:
                pass''')


class DictDataWriter(DictObjSource, DataWriter):
    """
    An implementation of an DataWriter that uses a dict to store things.

    An ObjSource offers the basic methods: __getitem__, __len__ and __iter__, along with the consequential
    mixin methods that collections.abc.Mapping adds automatically:
        __contains__, keys, items, values, get, __eq__, and __ne__

    >>> dw = DictDataWriter()  # make an empty data writer, and write two items
    >>> dw['foo'] = 'bar'
    >>> dw['hello'] = 'world'
    >>> len(dw)  # how many items do we have?
    2
    >>> list(dw)  # what are their keys?
    ['foo', 'hello']
    >>> list(dw.items())  # what (key, value) pairs do we have?
    [('foo', 'bar'), ('hello', 'world')]
    >>> list(dw.keys())  # just the keys (same as list(dw), but dw.keys() gives us a KeysView)
    ['foo', 'hello']
    >>> list(dw.values())  # see the values
    ['bar', 'world']
    >>> del dw['foo']  # delete 'foo'
    >>> list(dw)  # see that only 'hello' is left
    ['hello']
    >>>
    >>> # adding some more data
    >>> dw[42] = 'forty two'
    >>> dw[('e', 'mc', 2)] = 'tuple keys work'  # actually, any hashable can be a key!
    >>> list(dw)
    ['hello', 42, ('e', 'mc', 2)]
    >>>
    >>> dw.pop(('e', 'mc', 2))  # pop data (get the data stored in a key, and remove it)
    'tuple keys work'
    >>> list(dw)  # see what's left
    ['hello', 42]
    >>> dw.popitem()  # pop an arbitrary item
    ('hello', 'world')
    >>> list(dw)
    [42]
    >>> 42 in dw
    True
    >>> dw.setdefault('this key does not exist', 'this is my default')
    'this is my default'
    >>> list(dw)
    [42, 'this key does not exist']
    >>> list(dw.items())
    [(42, 'forty two'), ('this key does not exist', 'this is my default')]
    >>> dw.update({42: 'not forty two anymore'})
    >>> list(dw.items())
    [(42, 'not forty two anymore'), ('this key does not exist', 'this is my default')]
    >>> dw.clear()  # should be the "delete everything" method, but has been overridden for safe keeping
    <BLANKLINE>
            The MutableMapping clear method was overridden to make dangerous difficult.
            If you really want to delete all your data, you can do so by doing:
                try:
                    while True:
                        self.popitem()
                except KeyError:
                    pass
    """

    def __setitem__(self, k, v):
        self._d[k] = v

    def __delitem__(self, k):
        del self._d[k]
