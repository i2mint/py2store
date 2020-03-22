from collections.abc import Collection
import os
import re

from py2store.base import Store, KvCollection
from py2store.util import max_common_prefix
from py2store.key_mappers.paths import PrefixRelativizationMixin
from py2store.parse_format import match_re_for_fstring

file_sep = os.path.sep


def ensure_slash_suffix(path):
    if not path.endswith(file_sep):
        return path + file_sep
    else:
        return path


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


class PathFormat:
    def __init__(self, path_format: str):
        """
        A class for pattern-filtered exploration of file paths.
        :param path_format: The f-string format that the fullpath keys of the obj source should have.
            Often, just the root directory whose FILES contain the (full_filepath, content) data
            Also common is to use path_format='{rootdir}/{relative_path}.EXT' to impose a specific extension EXT
        """
        self._path_format = path_format  # not intended for use, but keeping in case, for now

        if '{' not in path_format:
            rootdir = ensure_slash_suffix(path_format)
            # if the path_format is equal to the _prefix (i.e. there's no {} formatting)
            # ... append a formatting element so that the matcher can match all subfiles.
            path_pattern = path_format + '{}'
        else:
            rootdir = ensure_slash_suffix(os.path.dirname(re.match('[^\{]*', path_format).group(0)))
            path_pattern = path_format

        self._prefix = rootdir
        self._path_match_re = match_re_for_fstring(path_pattern)

        def _key_filt(k):
            return bool(self._path_match_re.match(k))

        self._key_filt = _key_filt

    def is_valid_key(self, k):
        return self._key_filt(k)


class ExpliticKeyTrans:
    def __init__(self, id_of_key=None, key_of_id=None):
        if id_of_key is None:
            if key_of_id is None:
                raise ValueError("You need to specify at least one of these: id_of_key, or key_of_id (or both!)")
            else:
                id_of_key = {k: _id for _id, k in key_of_id.items()}
        elif key_of_id is None:
            key_of_id = {_id: k for k, _id in id_of_key.items()}
        self.id_of_key = id_of_key
        self.key_of_id = key_of_id

    def _key_of_id(self, _id):
        return self.key_of_id[_id]

    def _id_of_key(self, k):
        return self.id_of_key[k]

    # TODO: These two functions are general and should be placed in another Mixin or function
    def _test_key_id_key_invertability(self, k):
        return k == self._key_of_id(self._id_of_key(k))

    def _test_id_key_id_invertability(self, _id):
        return _id == self._id_of_key(self._key_of_id(_id))


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
