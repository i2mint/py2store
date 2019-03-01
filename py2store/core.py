from collections.abc import Mapping, Collection
from typing import Callable
from py2store.base import AbstractObjReader
from py2store.util import lazyprop


class PrefixRelativization:
    """
    Mixin that adds a intercepts the _id_of_key an _key_of_id methods, transforming absolute keys to relative ones.
    Designed to work with string keys, where absolute and relative are relative to a _prefix attribute
    (assumed to exist).
    The cannonical use case is when keys are absolute file paths, but we want to identify data through relative paths.

    When subclassed, should be placed before the class defining _id_of_key an _key_of_id.
    Also, assumes that a (string) _prefix attribute will be available.

    >>> from py2store.base import KeyValidation, StoreInterface
    >>> from collections import UserDict
    >>>
    >>> class DictStore(PrefixRelativization, StoreInterface, UserDict):
    ...     def __init__(self, _prefix='/root/of/data/', *args, **kwargs):
    ...         super().__init__(*args, **kwargs)
    ...         self._prefix = _prefix
    ...
    >>> # In the above, UserDict provides the actual physical data storage, StoreInterface the key and value wraps,
    >>> # and PrefixRelativization the extra absolute/relative layer.
    >>> s = DictStore()
    >>> s['foo'] = 'bar'
    >>> assert s['foo'] == 'bar'
    >>> s['too'] = 'much'
    >>> assert list(s.keys()) == ['foo', 'too']
    >>> # Everything looks normal, but are the actual keys behind the hood?
    >>> s._id_of_key('foo')
    '/root/of/data/foo'
    >>> # see when iterating over s.items(), we get the interface view:
    >>> list(s.items())
    [('foo', 'bar'), ('too', 'much')]
    >>> # but if we just print those items, we see under the hood (as long as __str__ and __repr__ are not wrapped)
    >>> print(s.items())
    ItemsView({'/root/of/data/foo': 'bar', '/root/of/data/too': 'much'})
    """
    @lazyprop
    def _prefix_length(self):
        return len(self._prefix)

    def _id_of_key(self, k):
        return super()._id_of_key(self._prefix + k)

    def _key_of_id(self, _id):
        return super()._key_of_id(_id[self._prefix_length:])


class ExplicitKeys:
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


class ObjReader(AbstractObjReader):
    """
    py2store.base.AbstractObjReader implementation that uses a specified function to get the contents for a given key.

    >>> # define a contents_of_key that reads stuff from a dict
    >>> data = {'foo': 'bar', 42: "everything"}
    >>> def read_dict(k):
    ...     return data[k]
    >>> pr = ObjReader(contents_of_key=read_dict)
    >>> pr['foo']
    'bar'
    >>> pr[42]
    'everything'
    >>>
    >>> # define contents_of_key that reads stuff from a file given it's path
    >>> def read_file(path):
    ...     with open(path) as fp:
    ...         return fp.read()
    >>> pr = ObjReader(contents_of_key=read_file)
    >>> file_where_this_code_is = __file__  # it should be THIS file you're reading right now!
    >>> print(pr[file_where_this_code_is][:100])  # print the first 100 characters of this file
    from collections.abc import Mapping, Collection
    from typing import Callable
    from py2store.base impor
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


class ExplicitKeysSource(ExplicitKeys, ObjReader, Mapping):
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
