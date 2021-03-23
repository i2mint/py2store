"""
This module contains key-value views of disparate sources.
"""
from typing import Mapping, Iterable, Optional, Callable, Union
from operator import itemgetter
from itertools import groupby as itertools_groupby

from py2store.base import KvReader, KvPersister
from py2store.trans import cached_keys
from py2store.caching import mk_cached_store
from py2store.util import copy_attrs
from py2store.utils.signatures import Sig


def identity_func(x):
    return x


def inclusive_subdict(d, include):
    return {k: d[k] for k in d.keys() & include}


def exclusive_subdict(d, exclude):
    return {k: d[k] for k in d.keys() - exclude}


class NotUnique(ValueError):
    """Raised when an iterator was expected to have only one element, but had more"""


NoMoreElements = type('NoMoreElements', (object,), {})()


def unique_element(iterator):
    element = next(iterator)
    if next(iterator, NoMoreElements) is not NoMoreElements:
        raise NotUnique("iterator had more than one element")
    return element


KvSpec = Union[
    Callable,
    Iterable[Union[str, int]],
    str,
    int
]


def _kv_spec_to_func(kv_spec: KvSpec) -> Callable:
    if isinstance(kv_spec, (str, int)):
        return itemgetter(kv_spec)
    elif isinstance(kv_spec, Iterable):
        return itemgetter(*kv_spec)
    elif kv_spec is None:
        return identity_func
    return kv_spec


# TODO: This doesn't work
# KvSpec.from = _kv_spec_to_func  # I'd like to be able to couple KvSpec and it's conversion function (even more: __call__ instead of from)


class SequenceKvReader(KvReader):
    """
    A KvReader that sources itself in an iterable of elements from which keys and values will be extracted and
    grouped by key.

    >>> docs = [{'_id': 0, 's': 'a', 'n': 1},
    ...  {'_id': 1, 's': 'b', 'n': 2},
    ...  {'_id': 2, 's': 'b', 'n': 3}]
    >>>

    Out of the box, SequenceKvReader gives you enumerated integer indices as keys, and the sequence items as is, as vals

    >>> s = SequenceKvReader(docs)
    >>> list(s)
    [0, 1, 2]
    >>> s[1]
    {'_id': 1, 's': 'b', 'n': 2}
    >>> assert s.get('not_a_key') is None

    You can make it more interesting by specifying a val function to compute the vals from the sequence elements

    >>> s = SequenceKvReader(docs, val=lambda x: (x['_id'] + x['n']) * x['s'])
    >>> assert list(s) == [0, 1, 2]  # as before
    >>> list(s.values())
    ['a', 'bbb', 'bbbbb']

    But where it becomes more useful is when you specify a key as well.
    SequenceKvReader will then compute the keys with that function, group them, and return as the value, the
    list of sequence elements that match that key.

    >>> s = SequenceKvReader(docs,
    ...         key=lambda x: x['s'],
    ...         val=lambda x: {k: x[k] for k in x.keys() - {'s'}})
    >>> assert list(s) == ['a', 'b']
    >>> assert s['a'] == [{'_id': 0, 'n': 1}]
    >>> assert s['b'] == [{'_id': 1, 'n': 2}, {'_id': 2, 'n': 3}]

    The cannonical form of key and val is a function, but if you specify a str, int, or iterable thereof,
    SequenceKvReader will make an itemgetter function from it, for your convenience.

    >>> s = SequenceKvReader(docs, key='_id')
    >>> assert list(s) == [0, 1, 2]
    >>> assert s[1] == [{'_id': 1, 's': 'b', 'n': 2}]

    The ``val_postproc`` argument is ``list`` by default, but what if we don't specify any?
    Well then you'll get an unconsumed iterable of matches

    >>> s = SequenceKvReader(docs, key='_id', val_postproc=None)
    >>> assert isinstance(s[1], Iterable)

    The ``val_postproc`` argument specifies what to apply to this iterable of matches.
    For example, you can specify ``val_postproc=next`` to simply get the first matched element:


    >>> s = SequenceKvReader(docs, key='_id', val_postproc=next)
    >>> assert list(s) == [0, 1, 2]
    >>> assert s[1] == {'_id': 1, 's': 'b', 'n': 2}

    We got the whole dict there. What if we just want we didn't want the _id, which is used by the key, in our val?

    >>> from functools import partial
    >>> all_but_s = partial(exclusive_subdict, exclude=['s'])
    >>> s = SequenceKvReader(docs, key='_id', val=all_but_s, val_postproc=next)
    >>> assert list(s) == [0, 1, 2]
    >>> assert s[1] == {'_id': 1, 'n': 2}

    Suppose we want to have the pair of ('_id', 'n') values as a key, and only 's' as a value...

    >>> s = SequenceKvReader(docs, key=('_id', 'n'), val='s', val_postproc=next)
    >>> assert list(s) == [(0, 1), (1, 2), (2, 3)]
    >>> assert s[1, 2] == 'b'

    But remember that using ``val_postproc=next`` will only give you the first match as a val.

    >>> s = SequenceKvReader(docs, key='s', val=all_but_s, val_postproc=next)
    >>> assert list(s) == ['a', 'b']
    >>> assert s['a'] == {'_id': 0, 'n': 1}
    >>> assert s['b'] == {'_id': 1, 'n': 2}   # note that only the first match is returned.

    If you do want to only grab the first match, but want to additionally assert that there is no more than one,
    you can specify this with ``val_postproc=unique_element``:

    >>> s = SequenceKvReader(docs, key='s', val=all_but_s, val_postproc=unique_element)
    >>> assert s['a'] == {'_id': 0, 'n': 1}
    >>> s['b']  # should raise an exception since there's more than one match
    Traceback (most recent call last):
      ...
    sources.NotUnique: iterator had more than one element

    """

    def __init__(
            self,
            sequence: Iterable,
            key: KvSpec = None,
            val: KvSpec = None,
            val_postproc=list
    ):
        """Make a SequenceKvReader instance,

        :param sequence: The iterable to source the keys and values from.
        :param key: Specification of how to extract a key from an iterable element.
            If None, will use integer keys from key, val = enumerate(iterable).
            key can be a callable, a str or int, or an iterable of strs and ints.
        :param val: Specification of how to extract a value from an iterable element.
            If None, will use the element as is, as the value.
            val can be a callable, a str or int, or an iterable of strs and ints.
        :param val_postproc: Function to apply to the iterable of vals.
            Default is ``list``, which will have the effect of values being lists of all vals matching a key.
            Another popular choice is ``next`` which will have the effect of values being the first matched to the key
        """
        self.sequence = sequence
        if key is not None:
            self.key = _kv_spec_to_func(key)
        else:
            self.key = None
        self.val = _kv_spec_to_func(val)
        self.val_postproc = val_postproc or identity_func
        assert isinstance(self.val_postproc, Callable)

    def kv_items(self):
        if self.key is not None:
            for k, v in itertools_groupby(self.sequence, key=self.key):
                yield k, self.val_postproc(map(self.val, v))
        else:
            for i, v in enumerate(self.sequence):
                yield i, self.val(v)

    def __getitem__(self, k):
        for kk, vv in self.kv_items():
            if kk == k:
                return vv
        raise KeyError(f"Key not found: {k}")

    def __iter__(self):
        yield from map(itemgetter(0), self.kv_items())


@cached_keys
class CachedKeysSequenceKvReader(SequenceKvReader):
    """SequenceKvReader but with keys cached. Use this one if you will perform multiple accesses to only some of the keys of the store"""


@mk_cached_store
class CachedSequenceKvReader(SequenceKvReader):
    """SequenceKvReader but with the whole mapping cached as a dict. Use this one if you will perform multiple accesses to the store"""


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
