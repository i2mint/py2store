from collections.abc import Collection

from py2store.util import lazyprop, max_common_prefix
from py2store.base import StoreBase, IdentityKvWrap


class PrefixRelativization:
    """
    Mixin that adds a intercepts the _id_of_key an _key_of_id methods, transforming absolute keys to relative ones.
    Designed to work with string keys, where absolute and relative are relative to a _prefix attribute
    (assumed to exist).
    The cannonical use case is when keys are absolute file paths, but we want to identify data through relative paths.

    When subclassed, should be placed before the class defining _id_of_key an _key_of_id.
    Also, assumes that a (string) _prefix attribute will be available.

    >>> from py2store.base import KeyValidation, StoreBase, IdentityKvWrap
    >>> from collections import UserDict
    >>>
    >>> class DictStore(PrefixRelativization, StoreBase, IdentityKvWrap, UserDict):
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
        return super()._key_of_id(_id)[self._prefix_length:]
        # return super()._key_of_id(_id[self._prefix_length:])


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


class ExplicitKeysWithPrefixRelativization(StoreBase, PrefixRelativization, IdentityKvWrap, ExplicitKeys):
    """
    py2store.base.Keys implementation that gets it's keys explicitly from a collection given at initialization time.
    The key_collection must be a collections.abc.Collection (such as list, tuple, set, etc.)

    >>> keys = ExplicitKeysWithPrefixRelativization(key_collection=['/root/of/foo', '/root/of/bar', '/root/for/alice'])
    >>> 'of/foo' in keys
    True
    >>> 'not there' in keys
    False
    >>> list(keys)
    ['of/foo', 'of/bar', 'for/alice']
    """
    __slots__ = ('_key_collection',)

    def __init__(self, key_collection: Collection, _prefix=None):
        super().__init__(key_collection=key_collection)
        if _prefix is None:
            _prefix = max_common_prefix(key_collection)
        self._prefix = _prefix
