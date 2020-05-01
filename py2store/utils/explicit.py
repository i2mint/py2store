from collections.abc import Mapping
from typing import Callable, Collection

from py2store import Store
from py2store.base import KvCollection, KvReader
from py2store.trans import kv_wrap
from py2store.key_mappers.paths import PrefixRelativizationMixin
from py2store.util import max_common_prefix


class ObjLoader(object):
    def __init__(self, data_of_key, obj_of_data=None):
        self.data_of_key = data_of_key
        if obj_of_data is not None or not callable(obj_of_data):
            raise TypeError('serializer must be None or a callable')
        self.obj_of_data = obj_of_data

    def __call__(self, k):
        if self.obj_of_data is not None:
            return self.obj_of_data(self.data_of_key(k))
        else:
            return self.data_of_key(k)


class ObjReader:
    """
    py2store.base.AbstractObjReader implementation that uses a specified function to get the contents for a given key.

    >>> # define a contents_of_key that reads stuff from a dict
    >>> data = {'foo': 'bar', 42: "everything"}
    >>> def read_dict(k):
    ...     return data[k]
    >>> pr = ObjReader(_obj_of_key=read_dict)
    >>> pr['foo']
    'bar'
    >>> pr[42]
    'everything'
    >>>
    >>> # define contents_of_key that reads stuff from a file given it's path
    >>> def read_file(path):
    ...     with open(path) as fp:
    ...         return fp.read()
    >>> pr = ObjReader(_obj_of_key=read_file)
    >>> file_where_this_code_is = __file__  # it should be THIS file you're reading right now!
    >>> print(pr[file_where_this_code_is][:100])  # print the first 100 characters of this file
    from collections.abc import Mapping, Collection
    from typing import Callable
    from py2store.util impor
    """

    def __init__(self, _obj_of_key: Callable):
        self._obj_of_key = _obj_of_key

    @classmethod
    def from_composition(cls, data_of_key, obj_of_data=None):
        return cls(_obj_of_key=ObjLoader(data_of_key=data_of_key, obj_of_data=obj_of_data))

    def __getitem__(self, k):
        try:
            return self._obj_of_key(k)
        except Exception as e:
            raise KeyError("KeyError in {} when trying to __getitem__({}): {}".format(
                e.__class__.__name__, k, e))


# TODO: Revisit ExplicitKeys and ExplicitKeysWithPrefixRelativization. Not extendible to full store!
class ExplicitKeys(KvCollection):
    """
    py2store.base.Keys implementation that gets it's keys explicitly from a collection given at initialization time.
    The key_collection must be a collections.abc.Collection (such as list, tuple, set, etc.)

    >>> keys = ExplicitKeys(key_collection=['foo', 'bar', 'alice'])
    >>> 'foo' in keys
    True
    >>> 'not there' in keys
    False
    >>> list(keys)
    ['foo', 'bar', 'alice']
    """

    __slots__ = ('_key_collection',)

    def __init__(self, key_collection: Collection):
        assert isinstance(key_collection, Collection), \
            "key_collection must be a collections.abc.Collection, i.e. have a __len__, __contains__, and __len__." \
            "The key_collection you gave me was a {}".format(type(key_collection))
        self._key_collection = key_collection

    def __iter__(self):
        yield from self._key_collection

    def __len__(self):
        return len(self._key_collection)

    def __contains__(self, k):
        return k in self._key_collection


class ExplicitKeysSource(ExplicitKeys, ObjReader, KvReader):
    """
    An object source that uses an explicit keys collection and a specified function to read contents for a key.
    """

    def __init__(self, key_collection: Collection, _obj_of_key: Callable):
        """

        :param key_collection: The collection of keys that this source handles
        :param _obj_of_key: The function that returns the contents for a key
        """
        ExplicitKeys.__init__(self, key_collection)
        ObjReader.__init__(self, _obj_of_key)


class ExplicitKeysStore(ExplicitKeys, Store):
    """Wrap a store (instance) so that it gets it's keys from an explicit iterable of keys.

    >>> s = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    >>> list(s)
    ['a', 'b', 'c', 'd']
    >>> ss = ExplicitKeysStore(s, ['d', 'a'])
    >>> len(ss)
    2
    >>> list(ss)
    ['d', 'a']
    >>> list(ss.values())
    [4, 1]
    >>> ss.head()
    ('d', 4)
    """

    def __init__(self, store, key_collection):
        Store.__init__(self, store)
        ExplicitKeys.__init__(self, key_collection)


class ExplicitKeyMap:
    def __init__(self, *, key_of_id: Mapping = None, id_of_key: Mapping = None):
        """

        :param key_of_id:
        :param id_of_key:

        >>> km = ExplicitKeyMap(key_of_id={'a': 1, 'b': 2})
        >>> km.id_of_key = {1: 'a', 2: 'b'}
        >>> km._key_of_id('b')
        2
        >>> km._id_of_key(1)
        'a'
        >>> # You can specify id_of_key instead
        >>> km = ExplicitKeyMap(id_of_key={1: 'a', 2: 'b'})
        >>> assert km.key_of_id_map == {'a': 1, 'b': 2}
        >>> # You can specify both key_of_id and id_of_key
        >>> km = ExplicitKeyMap(key_of_id={'a': 1, 'b': 2}, id_of_key={1: 'a', 2: 'b'})
        >>> assert km._key_of_id(km._id_of_key(2)) == 2
        >>> assert km._id_of_key(km._key_of_id('b')) == 'b'
        >>> # But they better be inverse of each other!
        >>> km = ExplicitKeyMap(key_of_id={'a': 1, 'b': 2, 'c': 2})
        Traceback (most recent call last):
          ...
        AssertionError: The values of key_of_id are not unique, so the mapping is not invertible
        >>> km = ExplicitKeyMap(key_of_id={'a': 1, 'b': 2}, id_of_key={1: 'a', 2: 'oh no!!!!'})
        Traceback (most recent call last):
          ...
        AssertionError: id_of_key and key_of_id_map are not inverse of each other!
        """
        if key_of_id is None and id_of_key is None:
            raise ValueError("You need to specify key_of_id_map, or id_of_key_map, or both")
        if key_of_id is None:
            assert hasattr(id_of_key, 'items')
            key_of_id = {v: k for k, v in id_of_key.items()}
            assert len(key_of_id) == len(id_of_key), \
                "The values of id_of_key are not unique, so the mapping is not invertible"
        elif id_of_key is None:
            assert hasattr(key_of_id, 'items')
            id_of_key = {v: k for k, v in key_of_id.items()}
            assert len(id_of_key) == len(key_of_id), \
                "The values of key_of_id are not unique, so the mapping is not invertible"
        else:
            assert (len(id_of_key) == len(key_of_id)) and (id_of_key == {v: k for k, v in key_of_id.items()}), \
                "id_of_key and key_of_id_map are not inverse of each other!"

        self.key_of_id_map = key_of_id
        self.id_of_key_map = id_of_key

    def _key_of_id(self, _id):
        return self.key_of_id_map[_id]

    def _id_of_key(self, k):
        return self.id_of_key_map[k]


class ExplicitKeymapReader(ExplicitKeys, Store):
    """Wrap a store (instance) so that it gets it's keys from an explicit iterable of keys.

    >>> s = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    >>> id_of_key = {'A': 'a', 'C': 'c'}
    >>> ss = ExplicitKeymapReader(s, id_of_key=id_of_key)
    >>> list(ss)
    ['A', 'C']
    >>> ss['C']  # will look up 'C', find 'c', and call the store on that.
    3
    """

    def __init__(self, store, key_of_id=None, id_of_key=None):
        key_trans = ExplicitKeyMap(key_of_id=key_of_id, id_of_key=id_of_key)
        Store.__init__(self, kv_wrap(key_trans)(store))
        ExplicitKeys.__init__(self, id_of_key.keys())


class ExplicitKeysWithPrefixRelativization(PrefixRelativizationMixin, Store):
    """
    py2store.base.Keys implementation that gets it's keys explicitly from a collection given at initialization time.
    The key_collection must be a collections.abc.Collection (such as list, tuple, set, etc.)

    >>> from py2store.base import Store
    >>> s = ExplicitKeysWithPrefixRelativization(key_collection=['/root/of/foo', '/root/of/bar', '/root/for/alice'])
    >>> keys = Store(store=s)
    >>> 'of/foo' in keys
    True
    >>> 'not there' in keys
    False
    >>> list(keys)
    ['of/foo', 'of/bar', 'for/alice']
    """
    __slots__ = ('_key_collection',)

    def __init__(self, key_collection, _prefix=None):
        if _prefix is None:
            _prefix = max_common_prefix(key_collection)
        store = ExplicitKeys(key_collection=key_collection)
        self._prefix = _prefix
        super().__init__(store=store)


class ObjDumper(object):
    def __init__(self, save_data_to_key, data_of_obj=None):
        self.save_data_to_key = save_data_to_key
        if data_of_obj is not None or not callable(data_of_obj):
            raise TypeError('serializer must be None or a callable')
        self.data_of_obj = data_of_obj

    def __call__(self, k, v):
        if self.data_of_obj is not None:
            return self.save_data_to_key(k, self.data_of_obj(v))
        else:
            return self.save_data_to_key(k, v)