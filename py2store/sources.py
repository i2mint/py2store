# from py2store.util import lazyprop, num_of_args
from py2store import KvReader, cached_keys


class FuncReader(KvReader):
    """Reader that seeds itself from a data fetching function list
    Uses the function list names as the keys, and their returned value as the values.

    For example: You have a list of urls that contain the data you want to have access to.
    You can write functions that bare the names you want to give to each dataset, and have the function
    fetch the data from the url, extract the data from the response and possibly prepare it
    (we advise minimally, since you can always transform from the raw source, but the opposite can be impossible).

    >>> def foo():
    ...     return 'bar'
    >>> def pi():
    ...     return 3.14159
    >>> s = FuncReader([foo, pi])
    >>> list(s)
    ['foo', 'pi']
    >>> s['foo']
    'bar'
    >>> s['pi']
    3.14159
    """

    def __init__(self, funcs):
        # TODO: assert no free arguments (arguments are allowed but must all have defaults)
        self.funcs = funcs
        self._func_of_name = {func.__name__: func for func in funcs}

    def __contains__(self, k):
        return k in self._func_of_name

    def __iter__(self):
        yield from self._func_of_name

    def __len__(self):
        return len(self._func_of_name)

    def __getitem__(self, k):
        return self._func_of_name[k]()  # call the func


import os

psep = os.path.sep

ddir = lambda o: [x for x in dir(o) if not x.startswith('_')]


def not_underscore_prefixed(x):
    return not x.startswith('_')


def _path_to_module_str(path, root_path):
    assert path.endswith('.py')
    path = path[:-3]
    if root_path.endswith(psep):
        root_path = root_path[:-1]
    root_path = os.path.dirname(root_path)
    len_root = len(root_path) + 1
    path_parts = path[len_root:].split(psep)
    if path_parts[-1] == '__init__.py':
        path_parts = path_parts[:-1]
    return '.'.join(path_parts)


# Pattern:
@cached_keys(keys_cache=set, name='Ddir')
class Ddir(KvReader):
    def __init__(self, obj, key_filt=not_underscore_prefixed):
        self._source = obj
        self._key_filt = key_filt
        if hasattr(obj, '__name__'):
            self.__name__ = obj.__name__
        if hasattr(obj, '__qualname__'):
            self.__qualname__ = obj.__qualname__

    @classmethod
    def module_from_path(cls, path, key_filt=not_underscore_prefixed, name=None, root_path=None):
        import importlib.util
        if name is None:
            if root_path is not None:
                try:
                    name = _path_to_module_str(path, root_path)
                except Exception:
                    name = 'fake.module.name'
        spec = importlib.util.spec_from_file_location(name, path)
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        return cls(foo, key_filt)

    def __iter__(self):
        yield from filter(self._key_filt, dir(self._source))

    def __getitem__(self, k):
        return self.__class__(getattr(self._source, k))

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self._source}, {self._key_filt})"
