from collections.abc import Mapping
from py2store.base import Keys, ObjReader


class PathListKeys(Keys):
    """
    py2store.base.Keys implementation that gets it's keys explicitly from a collection given at initialization time.
    >>> keys = PathListKeys(['foo', 'bar', 'alice'])
    >>> 'foo' in keys
    True
    >>> 'not there' in keys
    False
    >>> list(keys)
    ['foo', 'bar', 'alice']
    """
    __slots__ = ('_paths',)

    def __init__(self, paths):
        self._paths = paths

    def __iter__(self):
        yield from self._paths

    def __len__(self):
        return len(self._paths)

    def __contains__(self, k):
        return k in self._paths


class PathReader(ObjReader):
    """
    >>> def contents_of_path(path):
    ...     with open(path) as fp:
    ...         return fp.read()
    >>> pr = PathReader(contents_of_path)
    >>> file_where_this_code_is = __file__
    >>> print(pr[file_where_this_code_is][:100])  # print the first 100 characters of this file
    from collections.abc import Mapping
    from py2store.base import Keys, ObjReader
    """
    def __init__(self, contents_of_path):
        self._contents_of_path = contents_of_path

    def __getitem__(self, k):
        try:
            return self._contents_of_path(k)
        except Exception as e:
            raise KeyError("KeyError in {} when trying to __getitem__({}): {}".format(
                e.__class__.__name__, k, e))


class PathListSource(PathListKeys, PathReader, Mapping):
    def __init__(self, paths, contents_of_path):
        self._paths = paths
        # super().__init__(self, paths)
        self._contents_of_path = contents_of_path