from collections.abc import Collection

from py2store.base import Store
from py2store.util import max_common_prefix
from py2store.mixins import PrefixRelativizationMixin


class PrefixRelativization(PrefixRelativizationMixin):
    """A key wrap that allows one to interface with absolute paths through relative paths.
    The original intent was for local files. Instead of referencing files through an absolute path such as
        /A/VERY/LONG/ROOT/FOLDER/the/file/we.want
    we can instead reference the file as
        the/file/we.want

    But PrefixRelativization can be used, not only for local paths, but when ever a string reference is involved.
    In fact, not only strings, but any key object that has a __len__, __add__, and subscripting.
    """

    def __init__(self, _prefix=""):
        self._prefix = _prefix


# TODO: Revisit ExplicitKeys and ExplicitKeysWithPrefixRelativization. Not extendible to full store!
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
