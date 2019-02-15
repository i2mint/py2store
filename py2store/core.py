from collections.abc import Mapping, Collection
from typing import Callable
from py2store.base import Keys, AbstractObjReader


class ExplicitKeys(Keys):
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

    def __init__(self, contents_of_key: Callable):
        self._contents_of_key = contents_of_key

    def __getitem__(self, k):
        try:
            return self._contents_of_key(k)
        except Exception as e:
            raise KeyError("KeyError in {} when trying to __getitem__({}): {}".format(
                e.__class__.__name__, k, e))


class ExplicitKeysSource(ExplicitKeys, ObjReader, Mapping):
    """
    An object source that uses an explicit keys collection and a specified function to read contents for a key.
    """

    def __init__(self, key_collection: Collection, contents_of_key: Callable):
        """

        :param key_collection: The collection of keys that this source handles
        :param contents_of_key: The function that returns the contents for a key
        """
        ExplicitKeys.__init__(self, key_collection)
        ObjReader.__init__(self, contents_of_key)
