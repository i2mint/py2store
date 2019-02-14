from py2store.base import ObjSource


class DictObjSource(ObjSource):
    """
    An implementation of an ObjSource that uses a dict to store things
    An ObjSource offers the basic methods: __getitem__, __len__ and __iter__, along with the consequential
    mixin methods that collections.abc.Mapping adds automatically:
        __contains__, keys, items, values, get, __eq__, and __ne__
    >>> import collections
    >>>
    >>> o = DictObjSource(d={'a': 'foo', 'b': [1, 2, 3]})  # make a DictObjSource with two items
    >>> assert isinstance(DictObjSource(), collections.abc.Mapping)  # an DictObjSource instance is a Mapping
    >>> assert o['a'] == 'foo'  # the data stored in 'a' is 'foo'
    >>> assert len(o) == 2  # o has two items
    >>> assert list(o.__iter__()) == ['a', 'b']  # the keys of the two items are 'a' and 'b'
    >>> assert 'a' in o  # 'a' is a key of o
    >>> assert 'not there' not in o  # 'not there' is not a key of o
    >>> assert list(o.keys()) == ['a', 'b']  # the list of keys of o
    >>> assert list(o.values()) == ['foo', [1, 2, 3]]  # the values/datas stored by o
    >>> assert list(o.items()) == [('a', 'foo'), ('b', [1, 2, 3])]  # iterate over the (key, value) pairs of o
    >>> assert o.get('this key is not there') == None  # trying to get the value of a non-existing key returns None...
    >>> assert o.get('this key is not there', 'some default value') == 'some default value'  # ... or whatever you want
    >>> oo = DictObjSource(d={'b': [1, 2, 3], 'a': 'foo'})  # make another obj source
    >>> assert o == oo  # the objects are equal since all (key, value) items are equal (testing __eq__)
    >>> assert not o != oo  # (testing the dual operation, __neq__)
    >>> oo = DictObjSource(d={'a': 'foo', 'b': [1, 2, 3], 'c': 'bar'})  # lets make an obj source with one extra element
    >>> assert o != oo  # now o and oo are not equal
    >>> assert not o == oo  # ... as I just said
    """

    def __init__(self, d: dict = None):
        """

        :param d: The dict that contains the (key, value) data
        """
        if d is None:
            d = {}
        self._d = d

    def __getitem__(self, k):
        return self._d[k]

    def __len__(self):
        return len(self._d)

    def __iter__(self):
        return self._d.__iter__()

    def __contains__(self, k):  # override abstract version, which is not as efficient
        return k in self._d
