"""Tools to add caching layers to stores."""

import os
from functools import wraps, partial
from typing import Iterable, Callable
from inspect import signature

from py2store.trans import store_decorator


def is_a_cache(obj):
    return all(map(partial(hasattr, obj), ('__contains__', '__getitem__', '__setitem__')))


def get_cache(cache):
    """Convenience function to get a cache (whether it's already an instance, or needs to be validated)"""
    if is_a_cache(cache):
        return cache
    elif callable(cache) and len(signature(cache).parameters) == 0:
        return cache()  # consider it to be a cache factory, and call to make factory


########################################################################################################################
# Read caching

# The following is a "Cache-Aside" read-cache with NO builtin cache update or refresh mechanism.
def mk_memoizer(cache):
    def memoize(method):
        @wraps(method)
        def memoizer(self, k):
            if k not in cache:
                val = method(self, k)
                cache[k] = val  # cache it
                return val
            else:
                return cache[k]

        return memoizer

    return memoize


def _mk_cache_instance(cache=None, assert_attrs=()):
    """Make a cache store (if it's not already) from a type or a callable, or just return dict.
    Also assert the presence of given attributes

    >>> _mk_cache_instance(dict(a=1, b=2))
    {'a': 1, 'b': 2}
    >>> _mk_cache_instance(None)
    {}
    >>> _mk_cache_instance(dict)
    {}
    >>> _mk_cache_instance(list, ('__getitem__', '__setitem__'))
    []
    >>> _mk_cache_instance(tuple, ('__getitem__', '__setitem__'))
    Traceback (most recent call last):
        ...
    AssertionError: cache should have the __setitem__ method, but does not: ()

    """
    if isinstance(assert_attrs, str):
        assert_attrs = (assert_attrs,)
    if cache is None:
        cache = {}  # use a dict (memory caching) by default
    elif (isinstance(cache, type)  # if caching_store is a type...
          or (not hasattr(cache, '__getitem__')  # ... or is a callable without a __getitem__
              and callable(cache))):
        cache = cache()  # ... assume it's a no-argument callable that makes the instance
    for method in assert_attrs or ():
        assert hasattr(cache, method), f"cache should have the {method} method, but does not: {cache}"
    return cache


# TODO: Make it so that the resulting store gets arguments to construct it's own cache
#   right now, only cache instances or no-argument cache types can be used.
#

@store_decorator
def mk_cached_store(
        store=None,
        *,
        cache=dict
):
    """

    Args:
        store: The class of the store you want to cache
        cache: The store you want to use to cache. Anything with a __setitem__(k, v) and a __getitem__(k).
            By default, it will use a dict

    Returns: A subclass of the input store, but with caching (to the cache store)

    >>> from py2store.caching import mk_cached_store
    >>> import time
    >>> class SlowDict(dict):
    ...     sleep_s = 0.2
    ...     def __getitem__(self, k):
    ...         time.sleep(self.sleep_s)
    ...         return super().__getitem__(k)
    ...
    ...
    >>> d = SlowDict({'a': 1, 'b': 2, 'c': 3})
    >>>
    >>> d['a']  # Wow! Takes a long time to get 'a'
    1
    >>> cache = dict()
    >>> CachedSlowDict = mk_cached_store(store=SlowDict, cache=cache)
    >>>
    >>> s = CachedSlowDict({'a': 1, 'b': 2, 'c': 3})
    >>> print(f"store: {list(s)}\\ncache: {list(cache)}")
    store: ['a', 'b', 'c']
    cache: []
    >>> # This will take a LONG time because it's the first time we ask for 'a'
    >>> v = s['a']
    >>> print(f"store: {list(s)}\\ncache: {list(cache)}")
    store: ['a', 'b', 'c']
    cache: ['a']
    >>> # This will take very little time because we have 'a' in the cache
    >>> v = s['a']
    >>> print(f"store: {list(s)}\\ncache: {list(cache)}")
    store: ['a', 'b', 'c']
    cache: ['a']
    >>> # But we don't have 'b'
    >>> v = s['b']
    >>> print(f"store: {list(s)}\\ncache: {list(cache)}")
    store: ['a', 'b', 'c']
    cache: ['a', 'b']
    >>> # But now we have 'b'
    >>> v = s['b']
    >>> print(f"store: {list(s)}\\ncache: {list(cache)}")
    store: ['a', 'b', 'c']
    cache: ['a', 'b']
    >>> s['d'] = 4  # and we can do things normally (like put stuff in the store)
    >>> print(f"store: {list(s)}\\ncache: {list(cache)}")
    store: ['a', 'b', 'c', 'd']
    cache: ['a', 'b']
    >>> s['d']  # if we ask for it again though, it will take time (the first time)
    4
    >>> print(f"store: {list(s)}\\ncache: {list(cache)}")
    store: ['a', 'b', 'c', 'd']
    cache: ['a', 'b', 'd']
    >>> # Of course, we could write 'd' in the cache as well, to get it quicker,
    >>> # but that's another story: The story of write caches!
    >>>
    >>> # And by the way, your "cache wrapped" store hold a pointer to the cache it's using,
    >>> # so you can take a peep there if needed:
    >>> s._cache
    {'a': 1, 'b': 2, 'd': 4}
    """

    # cache = _mk_cache_instance(cache, assert_attrs=('__getitem__', '__setitem__'))
    assert isinstance(store, type), f"store should be a type, was a {type(store)}: {store}"

    class CachedStore(store):
        @wraps(store)
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._cache = _mk_cache_instance(cache, assert_attrs=('__getitem__', '__contains__', '__setitem__'))
            # self.__getitem__ = mk_memoizer(self._cache)(self.__getitem__)

        def __getitem__(self, k):
            if k not in self._cache:
                val = super().__getitem__(k)
                self._cache[k] = val  # cache it
                return val
            else:
                return self._cache[k]

    return CachedStore


cache_vals = mk_cached_store  # alias proposed for better name


@store_decorator
def mk_sourced_store(
        store=None,
        *,
        source=None,
        return_source_data=True
):
    """

    Args:
        store: The class of the store you want to cache
        cache: The store you want to use to cache. Anything with a __setitem__(k, v) and a __getitem__(k).
            By default, it will use a dict
        return_source_data:
    Returns: A subclass of the input store, but with caching (to the cache store)


    :param store: The class of the store you're talking to. This store acts as the cache
    :param source: The store that is used to populate the store (cache) when a key is missing there.
    :param return_source_data:
        If True, will return ``source[k]`` as is. This should be used only if ``store[k]`` would return the same.
        If False, will first write to cache (``store[k] = source[k]``) then return ``store[k]``.
        The latter introduces a performance hit (we write and then read again from the cache),
        but ensures consistency (and is useful if the writing or the reading to/from store
        transforms the data in some way.
    :return: A decorated store

    Here are two stores pretending to be local and remote data stores respectively.

    >>> from py2store.caching import mk_sourced_store
    >>>
    >>> class Local(dict):
    ...     def __getitem__(self, k):
    ...         print(f"looking for {k} in Local")
    ...         return super().__getitem__(k)
    >>>
    >>> class Remote(dict):
    ...     def __getitem__(self, k):
    ...         print(f"looking for {k} in Remote")
    ...         return super().__getitem__(k)


    Let's make a remote store with two elements in it, and a local store class that asks the remote store for stuff
    if it can't find it locally.

    >>> remote = Remote({'foo': 'bar', 'hello': 'world'})
    >>> SourcedLocal = mk_sourced_store(Local, source=remote)
    >>> s = SourcedLocal({'some': 'local stuff'})
    >>> list(s)  # the local store has one key
    ['some']

    # but if we ask for a key that is in the remote store, it provides it
    >>> assert s['foo'] == 'bar'
    looking for foo in Local
    looking for foo in Remote

    >>> list(s)
    ['some', 'foo']

    See that next time we ask for the 'foo' key, the local store provides it:

    >>> assert s['foo'] == 'bar'
    looking for foo in Local

    >>> assert s['hello'] == 'world'
    looking for hello in Local
    looking for hello in Remote
    >>> list(s)
    ['some', 'foo', 'hello']

    We can still add stuff (locally)...

    >>> s['something'] = 'else'
    >>> list(s)
    ['some', 'foo', 'hello', 'something']
    """
    assert source is not None, "You need to specify a source"

    source = _mk_cache_instance(source, assert_attrs=('__getitem__',))

    assert isinstance(store, type), f"store should be a type, was a {type(store)}: {store}"

    if return_source_data:
        class SourcedStore(store):
            _src = source

            def __missing__(self, k):
                # if you didn't have it "locally", ask src for it
                v = self._src[k]  # ... get it from _src,
                self[k] = v  # ... store it in self
                return v  # ... and return it.

    else:
        class SourcedStore(store):
            _src = source

            def __missing__(self, k):
                # if you didn't have it "locally", ask src for it
                v = self._src[k]  # ... get it from _src,
                self[k] = v  # ... store it in self
                return self[k]  # retrieve it again and return

    return SourcedStore


# cache = _mk_cache_instance(cache, assert_attrs=('__getitem__',))
# assert isinstance(store, type), f"store should be a type, was a {type(store)}: {store}"
#
# class CachedStore(store):
#     _cache = cache
#
#     @mk_memoizer(cache)
#     def __getitem__(self, k):
#         return super().__getitem__(k)
#
# return CachedStore


# TODO: Didn't finish this. Finish, doctest, and remove underscore
def _pre_condition_containment(store=None, *, bool_key_func):
    """Adds a custom boolean key function `bool_key_func` before the store_cls.__contains__ check is performed.

    It is meant to be used to create smart read caches.

    This can be used, for example, to perform TTL caching by having `bool_key_func` check on how long
    ago a cache item has been created, and returning False if the item is past it's expiry time.
    """

    class PreContaimentStore(store):
        def __contains__(self, k):
            return bool_key_func(k) and super().__contains__(k)

    return PreContaimentStore


def _slow_but_somewhat_general_hash(*args, **kwargs):
    """
    Attempts to create a hash of the inputs, recursively resolving the most common hurdles (dicts, sets, lists)
    Returns: A hash value for the input

    >>> _slow_but_somewhat_general_hash(1, [1, 2], a_set={1,2}, a_dict={'a': 1, 'b': [1,2]})
    ((1, (1, 2)), (('a_set', (1, 2)), ('a_dict', (('a', 1), ('b', (1, 2))))))
    """
    if len(kwargs) == 0 and len(args) == 1:
        single_val = args[0]
        if hasattr(single_val, "items"):
            return tuple(
                (k, _slow_but_somewhat_general_hash(v))
                for k, v in single_val.items()
            )
        elif isinstance(single_val, (set, list)):
            return tuple(single_val)
        else:
            return single_val
    else:
        return (
            tuple(_slow_but_somewhat_general_hash(x) for x in args),
            tuple(
                (k, _slow_but_somewhat_general_hash(v))
                for k, v in kwargs.items()
            ),
        )


# TODO: Could add an empty_cache function attribute.
#  Wrap the store cache to track new keys, and delete those (and only those!!) when emptying the store.
def store_cached(store, key_func: Callable):
    """
    Function output memorizer but using a specific (usually persisting) store as it's memory and a key_func to
    compute the key under which to store the output.

    The key can be
    - a single value under which the output should be stored, regardless of the input.
    - a key function that is called on the inputs to create a hash under which the function's output should be stored.

    Args:
        store: The key-value store to use for caching. Must support __getitem__ and __setitem__.
        key_func: The key function that is called on the input of the function to create the key value.

    Note: Union[Callable, Any] is equivalent to just Any, but reveals the two cases of a key more clearly.
    Note: No, Union[Callable, Hashable] is not better. For one, general store keys are not restricted to hashable keys.
    Note: No, they shouldn't.

    See Also: store_cached_with_single_key (for a version where the cache store key doesn't depend on function's args)

    >>> # Note: Our doc test will use dict as the store, but to make the functionality useful beyond existing
    >>> # RAM-memorizer, you should use actual "persisting" stores that store in local files, or DBs, etc.
    >>> store = dict()
    >>> @store_cached(store, lambda *args: args)
    ... def my_data(x, y):
    ...     print("Pretend this is a long computation")
    ...     return x + y
    >>> t = my_data(1, 2)  # note the print below (because the function is called
    Pretend this is a long computation
    >>> tt = my_data(1, 2)  # note there's no print (because the function is NOT called)
    >>> assert t == tt
    >>> tt
    3
    >>> my_data(3, 4)  # but different inputs will trigger the actual function again
    Pretend this is a long computation
    7
    >>> my_data._cache
    {(1, 2): 3, (3, 4): 7}
    """
    assert callable(key_func), (
        "key_func should be a callable: "
        "It's called on the wrapped function's input to make a key for the caching store."
    )

    def func_wrapper(func):
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            key = key_func(*args, **kwargs)
            if key in store:  # if the store has that key...
                return store[
                    key
                ]  # ... just return the data cached under this key
            else:  # if the store doesn't have it...
                output = func(
                    *args, **kwargs
                )  # ... call the function and get the output
                store[key] = output  # store the output under the key
                return output

        wrapped_func._cache = store
        return wrapped_func

    return func_wrapper


def store_cached_with_single_key(store, key):
    """
    Function output memorizer but using a specific store and key as it's memory.

    Use in situations where you have a argument-less function or bound method that computes some data whose dependencies
    are static enough that there's enough advantage to make the data refresh explicit (by deleting the cache entry)
    instead of making it implicit (recomputing/refetching the data every time).

    The key should be a single value under which the output should be stored, regardless of the input.

    Note: The wrapped function comes with a empty_cache attribute, which when called, empties the cache (i.e. removes
    the key from the store)

    Note: The wrapped function has a hidden `_cache` attribute pointing to the store in case you need to peep into it.

    Args:
        store: The cache. The key-value store to use for caching. Must support __getitem__ and __setitem__.
        key: The store key under which to store the output of the function.

    Note: Union[Callable, Any] is equivalent to just Any, but reveals the two cases of a key more clearly.
    Note: No, Union[Callable, Hashable] is not better. For one, general store keys are not restricted to hashable keys.
    Note: No, they shouldn't.

    See Also: store_cached (for a version whose keys are computed from the wrapped function's input.

    >>> # Note: Our doc test will use dict as the store, but to make the functionality useful beyond existing
    >>> # RAM-memorizer, you should use actual "persisting" stores that store in local files, or DBs, etc.
    >>> store = dict()
    >>> @store_cached_with_single_key(store, 'whatevs')
    ... def my_data():
    ...     print("Pretend this is a long computation")
    ...     return [1, 2, 3]
    >>> t = my_data()  # note the print below (because the function is called
    Pretend this is a long computation
    >>> tt = my_data()  # note there's no print (because the function is NOT called)
    >>> assert t == tt
    >>> tt
    [1, 2, 3]
    >>> my_data._cache  # peep in the cache
    {'whatevs': [1, 2, 3]}
    >>> # let's empty the cache
    >>> my_data.empty_cache_entry()
    >>> assert 'whatevs' not in my_data._cache  # see that the cache entry is gone.
    >>> t = my_data()  # so when you call the function again, it prints again!d
    Pretend this is a long computation
    """

    def func_wrapper(func):
        # TODO: Enforce that the func is argument-less or a bound method here?

        # TODO: WhyTF doesn't this work: (unresolved reference)
        # if key is None:
        #     key = '.'.join([func.__module__, func.__qualname___])

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            if key in store:  # if the store has that key...
                return store[
                    key
                ]  # ... just return the data cached under this key
            else:
                output = func(*args, **kwargs)
                store[key] = output
                return output

        wrapped_func._cache = store
        wrapped_func.empty_cache_entry = lambda: wrapped_func._cache.__delitem__(
            key
        )
        return wrapped_func

    return func_wrapper


def ensure_clear_to_kv_store(store):
    if not hasattr(store, "clear"):

        def _clear(kv_store):
            for k in kv_store:
                del kv_store[k]

        store.clear = _clear
    return store


def flush_on_exit(cls):
    new_cls = type(cls.__name__, (cls,), {})

    if not hasattr(new_cls, "__enter__"):
        def __enter__(self):
            return self

        new_cls.__enter__ = __enter__

    if not hasattr(new_cls, "__exit__"):

        def __exit__(self, *args, **kwargs):
            return self.flush_cache()

    else:  # TODO: Untested case where the class already has an __exit__, which we want to call after flush

        @wraps(new_cls.__exit__)
        def __exit__(self, *args, **kwargs):
            self.flush_cache()
            return super().__exit__(*args, **kwargs)

    new_cls.__exit__ = __exit__

    return new_cls


from py2store.util import has_enabled_clear_method


@store_decorator
def mk_write_cached_store(
        store=None,
        *,
        w_cache=dict,
        flush_cache_condition=None
):
    """Wrap a write cache around a store.

    Args:
        w_cache: The store to (write) cache to
        flush_cache_condition: The condition to apply to the cache
            to decide whether it's contents should be flushed or not

    A ``w_cache`` must have a clear method (that clears the cache's contents).
    If you know what you're doing and want to add one to your input kv store,
    you can do so by calling ``ensure_clear_to_kv_store(store)``
    -- this will add a ``clear`` method inplace AND return the resulting store as well.

    We didn't add this automatically because the first thing ``mk_write_cached_store`` will do is call clear,
    to remove all the contents of the store.
    You don't want to do this unwittingly and delete a bunch of precious data!!

    >>> from py2store.caching import mk_write_cached_store, ensure_clear_to_kv_store
    >>> from py2store import Store
    >>>
    >>> def print_state(store):
    ...     print(f"store: {store} ----- store._w_cache: {store._w_cache}")
    ...
    >>> class MyStore(dict): ...
    >>> MyCachedStore = mk_write_cached_store(MyStore, w_cache={})  # wrap MyStore with a (dict) write cache
    >>> s = MyCachedStore()  # make a MyCachedStore instance
    >>> print_state(s)  # print the contents (both store and cache), see that it's empty
    store: {} ----- store._w_cache: {}
    >>> s['hello'] = 'world'  # write 'world' in 'hello'
    >>> print_state(s)  # see that it hasn't been written
    store: {} ----- store._w_cache: {'hello': 'world'}
    >>> s['ding'] = 'dong'
    >>> print_state(s)
    store: {} ----- store._w_cache: {'hello': 'world', 'ding': 'dong'}
    >>> s.flush_cache()  # manually flush the cache
    >>> print_state(s)  # note that store._w_cache is empty, but store has the data now
    store: {'hello': 'world', 'ding': 'dong'} ----- store._w_cache: {}
    >>>
    >>> # But you usually want to use the store as a context manager
    >>> MyCachedStore = mk_write_cached_store(
    ...     MyStore, w_cache={},
    ...     flush_cache_condition=None)
    >>>
    >>> the_persistent_dict = dict()
    >>>
    >>> s = MyCachedStore(the_persistent_dict)
    >>> with s:
    ...     print("===> Before writing data:")
    ...     print_state(s)
    ...     s['hello'] = 'world'
    ...     print("===> Before exiting the with block:")
    ...     print_state(s)
    ...
    ===> Before writing data:
    store: {} ----- store._w_cache: {}
    ===> Before exiting the with block:
    store: {} ----- store._w_cache: {'hello': 'world'}
    >>>
    >>> print("===> After exiting the with block:"); print_state(s)  # Note that the cache store flushed!
    ===> After exiting the with block:
    store: {'hello': 'world'} ----- store._w_cache: {}
    >>>
    >>> # Example of auto-flushing when there's at least two elements
    >>> class MyStore(dict): ...
    ...
    >>> MyCachedStore = mk_write_cached_store(
    ...     MyStore, w_cache={},
    ...     flush_cache_condition=lambda w_cache: len(w_cache) >= 3)
    >>>
    >>> s = MyCachedStore()
    >>> with s:
    ...     for i in range(7):
    ...         s[i] = i * 10
    ...         print_state(s)
    ...
    store: {} ----- store._w_cache: {0: 0}
    store: {} ----- store._w_cache: {0: 0, 1: 10}
    store: {0: 0, 1: 10, 2: 20} ----- store._w_cache: {}
    store: {0: 0, 1: 10, 2: 20} ----- store._w_cache: {3: 30}
    store: {0: 0, 1: 10, 2: 20} ----- store._w_cache: {3: 30, 4: 40}
    store: {0: 0, 1: 10, 2: 20, 3: 30, 4: 40, 5: 50} ----- store._w_cache: {}
    store: {0: 0, 1: 10, 2: 20, 3: 30, 4: 40, 5: 50} ----- store._w_cache: {6: 60}
    >>> # There was still something left in the cache before exiting the with block. But now...
    >>> print_state(s)
    store: {0: 0, 1: 10, 2: 20, 3: 30, 4: 40, 5: 50, 6: 60} ----- store._w_cache: {}
    """

    w_cache = _mk_cache_instance(w_cache, ('clear', '__setitem__', 'items'))

    if not has_enabled_clear_method(w_cache):
        raise TypeError("""w_cache needs to have an enabled clear method to be able to act as a write cache.
        You can wrap w_cache in py2store.trans.ensure_clear_method to inject a clear method, 
        but BE WARNED: mk_write_cached_store will immediately delete all contents of `w_cache`!
        So don't give it your filesystem or important DB to delete!
        """)
    w_cache.clear()  # assure the cache is empty, by emptying it.

    @flush_on_exit
    class WriteCachedStore(store):
        _w_cache = w_cache
        _flush_cache_condition = staticmethod(flush_cache_condition)

        if flush_cache_condition is None:

            def __setitem__(self, k, v):
                return self._w_cache.__setitem__(k, v)

        else:
            assert callable(flush_cache_condition), (
                "flush_cache_condition must be None or a callable ",
                "taking the (write) cache store as an input and returning"
                "True if and only if the cache should be flushed.",
            )

            def __setitem__(self, k, v):
                r = self._w_cache.__setitem__(k, v)
                if self._flush_cache_condition(self._w_cache):
                    self.flush_cache()
                return r

        if not hasattr(store, "flush"):

            def flush(self, items: Iterable = tuple()):
                for k, v in items:
                    super().__setitem__(k, v)

        def flush_cache(self):
            self.flush(self._w_cache.items())
            return self._w_cache.clear()

    return WriteCachedStore


from collections import ChainMap, deque


class WriteBackChainMap(ChainMap):
    max_key_search_depth = 1

    def __getitem__(self, key):
        q = deque([])
        for mapping in self.maps:
            try:
                v = mapping[key]  # can't use 'key in mapping' with defaultdict
                for d in q:
                    d[key] = v
                return v
            except KeyError:
                q.append(mapping)
        return self.__missing__(key)

    def __len__(self):
        return len(set().union(*self.maps[:self.max_key_search_depth]))  # reuses stored hash values if possible

    def __iter__(self):
        d = {}
        for mapping in reversed(self.maps[:self.max_key_search_depth]):
            d.update(dict.fromkeys(mapping))  # reuses stored hash values if possible
        return iter(d)

    def __contains__(self, key):
        return any(key in m for m in self.maps[:self.max_key_search_depth])


# Experimental #########################################################################################################

def _mk_cache_method_local_path_key(method, args, kwargs, ext='.p', path_sep=os.path.sep):
    """"""
    return (
            method.__module__ + path_sep +
            method.__qualname__ + path_sep +
            (
                    ",".join(map(str, args))
                    + ",".join(f"{k}={v}" for k, v in kwargs.items())
                    + ext
            )
    )


class HashableMixin:
    def __hash__(self):
        return id(self)


class HashableDict(HashableMixin, dict):
    """Just a dict, but hashable"""


# NOTE: cache uses (func, args, kwargs). Don't want to make more complex with a bind cast to (func, kwargs) only
def cache_func_outputs(cache=HashableDict):
    cache = get_cache(cache)

    def cache_method_decorator(func):
        @wraps(func)
        def _func(*args, **kwargs):
            k = (func, args, HashableDict(kwargs))
            if k not in cache:
                val = func(*args, **kwargs)
                cache[k] = val  # cache it
                return val
            else:
                return cache[k]

        return _func

    return cache_method_decorator

# from py2store import StrTupleDict
#
# def process_fak(module, qualname, args, kwargs):
# #     func, args, kwargs = map(fak_dict.get, ('func', 'args', 'kwargs'))
#     return {
#         'module': module,
#         'qualname': qualname,
#         'args': ",".join(map(str, args)),
#         'kwargs': ",".join(f"{k}={v}" for k, v in kwargs.items())
#     }
#
# t = StrTupleDict(os.path.join("{module}", "{qualname}", "{args},{kwargs}.p"), process_kwargs=process_fak)
#
# t.tuple_to_str((StrTupleDict.__module__, StrTupleDict.__qualname__, (1, 'one'), {'mode': 'lydian'}))
