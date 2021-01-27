from typing import Mapping, Optional
from inspect import getsource

# from py2store.util import lazyprop, num_of_args
from py2store import KvReader, KvPersister, cached_keys
from py2store.util import copy_attrs
from py2store.utils.signatures import Sig


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
        self._func = {func.__name__: func for func in funcs}

    def __contains__(self, k):
        return k in self._func

    def __iter__(self):
        yield from self._func

    def __len__(self):
        return len(self._func)

    def __getitem__(self, k):
        return self._func[k]()  # call the func


class FuncDag(FuncReader):
    def __init__(self, funcs, **kwargs):
        super().__init__(funcs)
        self._sig = {fname: Sig(func) for fname, func in self._func.items()}
        # self._input_names = sum(self._sig)

    def __getitem__(self, k):
        return self._func_of_name[k]()  # call the func


import os

psep = os.path.sep

ddir = lambda o: [x for x in dir(o) if not x.startswith("_")]


def not_underscore_prefixed(x):
    return not x.startswith("_")


def _path_to_module_str(path, root_path):
    assert path.endswith(".py")
    path = path[:-3]
    if root_path.endswith(psep):
        root_path = root_path[:-1]
    root_path = os.path.dirname(root_path)
    len_root = len(root_path) + 1
    path_parts = path[len_root:].split(psep)
    if path_parts[-1] == "__init__.py":
        path_parts = path_parts[:-1]
    return ".".join(path_parts)


class ObjReader(KvReader):
    def __init__(self, obj):
        self.src = obj
        copy_attrs(
            target=self,
            source=self.src,
            attrs=("__name__", "__qualname__", "__module__"),
            raise_error_if_an_attr_is_missing=False
        )

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.src})"

    @property
    def _source(self):
        from warnings import warn

        warn("Deprecated: Use .src instead of ._source", DeprecationWarning, 2)
        return self.src


# class SourceReader(KvReader):
#     def __getitem__(self, k):
#         return getsource(k)

# class NestedObjReader(ObjReader):
#     def __init__(self, obj, src_to_key, key_filt=None, ):

# Pattern: Recursive navigation
# Note: Moved dev to independent package called "guide"
@cached_keys(keys_cache=set, name="Attrs")
class Attrs(ObjReader):
    def __init__(self, obj, key_filt=not_underscore_prefixed):
        super().__init__(obj)
        self._key_filt = key_filt

    @classmethod
    def module_from_path(
            cls, path, key_filt=not_underscore_prefixed, name=None, root_path=None
    ):
        import importlib.util

        if name is None:
            if root_path is not None:
                try:
                    name = _path_to_module_str(path, root_path)
                except Exception:
                    name = "fake.module.name"
        spec = importlib.util.spec_from_file_location(name, path)
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        return cls(foo, key_filt)

    def __iter__(self):
        yield from filter(self._key_filt, dir(self.src))

    def __getitem__(self, k):
        return self.__class__(getattr(self.src, k))

    def __repr__(self):
        return f"{self.__class__.__qualname__}({self.src}, {self._key_filt})"


Ddir = Attrs  # for back-compatibility, temporarily


# TODO: Make it work with a store, without having to load and store the values explicitly.
class DictAttr(KvPersister):
    """Convenience class to hold Key-Val pairs with both a dict-like and struct-like interface.
    The dict-like interface has just the basic get/set/del/iter/len
    (all "dunders": none visible as methods). There is no get, update, etc.
    This is on purpose, so that the only visible attributes (those you get by tab-completion for instance)
    are the those you injected.

    >>> da = DictAttr(foo='bar', life=42)
    >>> da.foo
    'bar'
    >>> da['life']
    42
    >>> da.true = 'love'
    >>> len(da)  # count the number of fields
    3
    >>> da['friends'] = 'forever'  # write as dict
    >>> da.friends  # read as attribute
    'forever'
    >>> list(da)  # list fields (i.e. keys i.e. attributes)
    ['foo', 'life', 'true', 'friends']
    >>> list(da.items())
    [('foo', 'bar'), ('life', 42), ('true', 'love'), ('friends', 'forever')]
    >>> del da['friends']  # delete as dict
    >>> del da.foo # delete as attribute
    >>> list(da)
    ['life', 'true']
    >>> da._source  # the hidden dict that is wrapped
    {'life': 42, 'true': 'love'}
    """

    _source = None

    def __init__(self, _source: Optional[Mapping] = None, **keys_and_values):
        if _source is not None:
            assert isinstance(_source, Mapping)
            self._source = _source
        else:
            super().__setattr__("_source", {})
            for k, v in keys_and_values.items():
                setattr(self, k, v)

    def __getitem__(self, k):
        return self._source[k]

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def __delitem__(self, k):
        delattr(self, k)

    def __iter__(self):
        return iter(self._source.keys())

    def __len__(self):
        return len(self._source)

    def __setattr__(self, k, v):
        self._source[k] = v
        super().__setattr__(k, v)

    def __delattr__(self, k):
        del self._source[k]
        super().__delattr__(k)
