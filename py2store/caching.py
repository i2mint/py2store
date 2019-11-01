from functools import wraps
from typing import Iterable


########################################################################################################################
# Read caching

# The following is a "Cache-Aside" read-cache with NO builtin cache update or refresh mechanism.
def mk_memoizer(cache_store):
    def memoize(method):
        @wraps(method)
        def memoizer(self, k):
            if k not in cache_store:
                val = method(self, k)
                cache_store[k] = val  # cache it
                return val
            else:
                return cache_store[k]

        return memoizer

    return memoize


def mk_cached_store(store_cls_you_want_to_cache, caching_store=None):
    """

    Args:
        store_cls_you_want_to_cache: The class of the store you want to cache
        caching_store: The store you want to use to cacheAnything with a __setitem__(k, v) and a __getitem__(k).
            By default, it will use a dict

    Returns: A subclass of the input store_cls_you_want_to_cache, but with caching (to caching_store)

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
    >>> CachedSlowDict = mk_cached_store(store_cls_you_want_to_cache=SlowDict, caching_store=cache)
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
    >>> s._caching_store
    {'a': 1, 'b': 2, 'd': 4}
    """
    if caching_store is None:
        caching_store = {}  # use a dict (memory caching) by default

    class CachedStore(store_cls_you_want_to_cache):
        _caching_store = caching_store

        @mk_memoizer(caching_store)
        def __getitem__(self, k):
            return super().__getitem__(k)

    return CachedStore


def ensure_clear_to_kv_store(store):
    if not hasattr(store, 'clear'):
        def _clear(kv_store):
            for k in kv_store:
                del kv_store[k]

        store.clear = _clear
    return store


def flush_on_exit(cls):
    new_cls = type(cls.__name__, (cls,), {})

    if not hasattr(new_cls, '__enter__'):
        def __enter__(self):
            return self

        new_cls.__enter__ = __enter__

    if not hasattr(new_cls, '__exit__'):
        def __exit__(self, *args, **kwargs):
            return self.flush_cache()
    else:  # TODO: Untested case where the class already has an __exit__, which we want to call after flush
        @wraps(new_cls.__exit__)
        def __exit__(self, *args, **kwargs):
            self.flush_cache()
            return super().__exit__(*args, **kwargs)
    new_cls.__exit__ = __exit__

    return new_cls


# t = self.flush_cache()
# if hasattr(store_cls_you_want_to_cache, '__exit__'):
#     t = super().__exit__(*args, **kwargs)
# return t

@flush_on_exit
def mk_write_cached_store(store_cls_you_want_to_cache,
                          w_cache=None,
                          flush_cache_condition=None):
    """

    Args:
        store_cls_you_want_to_cache:
        w_cache:
        flush_cache_condition:

    Returns:

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

    if w_cache is None:
        w_cache = {}  # use a dict (memory caching) by default

    if not hasattr(w_cache, 'clear'):
        raise TypeError("A w_cache must have a clear method (that clears the cache's contents). "
                        "If you know what you're doing and want to add one to your input kv store, "
                        "you can do so by calling ensure_clear_to_kv_store(store) -- this will add a "
                        "clear method inplace AND return the resulting store as well."
                        "We didn't add this automatically because the first thing mk_write_cached_store "
                        "will do is call clear, to remove all the contents of the store."
                        "You don't want to do this unwittingly and delete a bunch of precious data!!!")

    w_cache.clear()

    class WriteCachedStore(store_cls_you_want_to_cache):
        _w_cache = w_cache
        _flush_cache_condition = staticmethod(flush_cache_condition)

        if flush_cache_condition is None:
            def __setitem__(self, k, v):
                return self._w_cache.__setitem__(k, v)
        else:
            assert callable(flush_cache_condition), ("flush_cache_condition must be None or a callable ",
                                                     "taking the (write) cache store as an input and returning"
                                                     "True if and only if the cache should be flushed.")

            def __setitem__(self, k, v):
                r = self._w_cache.__setitem__(k, v)
                if self._flush_cache_condition(self._w_cache):
                    self.flush_cache()
                return r

        if not hasattr(store_cls_you_want_to_cache, 'flush'):
            def flush(self, items: Iterable = tuple()):
                for k, v in items:
                    super().__setitem__(k, v)

        def flush_cache(self):
            self.flush(self._w_cache.items())
            return self._w_cache.clear()

    return WriteCachedStore
