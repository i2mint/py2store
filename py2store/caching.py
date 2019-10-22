from functools import wraps, reduce
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

        def __enter__(self):
            return self

        def __exit__(self, *args, **kwargs):
            t = self.flush_cache()
            if hasattr(store_cls_you_want_to_cache, '__exit__'):
                t = super().__exit__(*args, **kwargs)
            return t

    return WriteCachedStore


import itertools
import time


def let_through(gen):
    yield from gen


def key_count(gen, start=0):
    yield from enumerate(gen, start=start)


def join_byte_values_and_key_as_current_utc_milliseconds(gen):
    k = int(time.time() * 1000)
    yield k, b''.join(gen)


def join_string_values_and_key_as_current_utc_milliseconds(gen):
    k = int(time.time() * 1000)
    yield k, ''.join(gen)


def mk_kv_from_keygen(keygen=itertools.count()):
    def aggregate(gen):
        for k, v in zip(keygen, gen):
            yield k, v

    return aggregate


infinite_keycount_kvs = mk_kv_from_keygen(keygen=itertools.count())

from operator import add
from collections import defaultdict

no_initial = type('NoInitial', (), {})()


def mk_group_aggregator(item_to_kv, aggregator_op=add, initial=no_initial):
    """Make a generator transforming function that will
    (a) make a key for each given item,
    (b) group all items according to the key

    Args:
        item_to_kv:
        aggregator_op:
        initial:

    Returns:

    >>> # Collect words (as a csv string), grouped by the lower case of the first letter
    >>> ag = mk_group_aggregator(lambda item: (item[0].lower(), item),
    ...                          aggregator_op=lambda x, y: ', '.join([x, y]))
    >>> list(ag(['apple', 'bananna', 'Airplane']))
    [('a', 'apple, Airplane'), ('b', 'bananna')]
    >>> # Collect (and concatinate)  characters according to their ascii value modulo 3
    >>> ag = mk_group_aggregator(lambda item: (item['age'], item['thing']),
    ...                          aggregator_op=lambda x, y: x + [y],
    ...                          initial=[])
    >>> list(ag([{'age': 0, 'thing': 'new'}, {'age': 42, 'thing': 'every'}, {'age': 0, 'thing': 'just born'}]))
    [(0, ['new', 'just born']), (42, ['every'])]
    """
    if initial is no_initial:
        aggregate_reduce = lambda v: reduce(aggregator_op, v)
    else:
        aggregate_reduce = lambda v: reduce(aggregator_op, v, initial)

    def aggregator(gen):
        d = defaultdict(list)
        for k, v in map(item_to_kv, gen):
            d[k].append(v)
        yield from ((k, aggregate_reduce(v)) for k, v in d.items())

    return aggregator


def mk_group_aggregator_with_key_func(item_to_key, aggregator_op=add, initial=no_initial):
    """Make a generator transforming function that will
    (a) make a key for each given item,
    (b) group all items according to the key

    Args:
        item_to_key: Function that takes an item of the generator and outputs the key that should be used to group items
        aggregator_op:  The aggregation binary function that is used to aggregate two items together.
            The function is used as is by the functools.reduce, applied to the sequence of items that were collected for
            a given group
        initial: The "empty" element to start the reduce (aggregation) with, if necessary.

    Returns:

    >>> # Collect words (as a csv string), grouped by the lower case of the first letter
    >>> ag = mk_group_aggregator_with_key_func(lambda item: item[0].lower(),
    ...                          aggregator_op=lambda x, y: ', '.join([x, y]))
    >>> list(ag(['apple', 'bananna', 'Airplane']))
    [('a', 'apple, Airplane'), ('b', 'bananna')]
    >>>
    >>> # Collect (and concatenate) characters according to their ascii value modulo 3
    ... ag = mk_group_aggregator_with_key_func(lambda item: (ord(item) % 3))
    >>> list(ag('abcdefghijklmnop'))
    [(1, 'adgjmp'), (2, 'behkn'), (0, 'cfilo')]
    >>>
    >>> # sum all even and odd number separately
    ... ag = mk_group_aggregator_with_key_func(lambda item: (item % 2))
    >>> list(ag([1, 2, 3, 4, 5]))  # sum of evens is 6, and sum of odds is 9
    [(1, 9), (0, 6)]
    >>>
    >>> # if we wanted to collect all odds and evens, we'd need a different aggregator and initial
    ... ag = mk_group_aggregator_with_key_func(lambda item: (item % 2), aggregator_op=lambda x, y: x + [y], initial=[])
    >>> list(ag([1, 2, 3, 4, 5]))
    [(1, [1, 3, 5]), (0, [2, 4])]
    """
    return mk_group_aggregator(item_to_kv=lambda item: (item_to_key(item), item),
                               aggregator_op=aggregator_op, initial=initial)


class CumulAggregWrite:
    """
    >>> store = dict()
    >>> key_count = lambda gen: enumerate(gen, start=0)
    >>> caw = CumulAggregWrite(store, cache_to_kv=key_count)
    >>> # Adding 3 items...
    >>> caw.append(3)
    >>> caw.append('hi')
    >>> caw.append({'a': complex, 'obj': [1,2,3]})
    >>>
    >>> caw.cache  # The cache now has 3 items
    [3, 'hi', {'a': <class 'complex'>, 'obj': [1, 2, 3]}]
    >>> caw.store  # Store is still empty
    {}
    >>> # Flushing the items #############
    >>> caw.flush_cache()
    >>> caw.cache  # The cache now has no more items
    []
    >>> caw.store  # But the store has them.
    {0: 3, 1: 'hi', 2: {'a': <class 'complex'>, 'obj': [1, 2, 3]}}
    >>>
    >>> # One common use case of aggregating is when data is actually grouped and aggregated for storage
    >>>
    """

    def __init__(self, store, cache_to_kv=infinite_keycount_kvs, mk_cache=list):
        self.store = store
        self.cache_to_kv = cache_to_kv
        self._mk_cache = mk_cache
        self.cache = mk_cache()  # Note: Better a cache factory, or the same object with an empty() method.

    def __setitem__(self, k, v):
        self.cache.append((k, v))

    def append(self, item):
        self.cache.append(item)

    def flush_cache(self):
        for k, v in self.cache_to_kv(self.cache):
            self.store[k] = v
        self.cache = self._mk_cache()

    def close(self):
        return self.flush_cache()


class CumulAggregWriteKvItems(CumulAggregWrite):
    def __init__(self, store):
        super().__init__(store, cache_to_kv=lambda gen: iter(gen), mk_cache=list)


class CumulAggregWriteWithAutoFlush(CumulAggregWrite):
    def __init__(self, store, cache_to_kv=infinite_keycount_kvs, mk_cache=list,
                 flush_cache_condition=lambda x: len(x) > 0):
        super().__init__(store, cache_to_kv, mk_cache)
        self.flush_cache_condition = flush_cache_condition

    def __setitem__(self, k, v):
        super().__setitem__(k, v)
        if self.flush_cache_condition(self.cache):
            self.flush_cache()

    def append(self, item):
        super().append(item)
        if self.flush_cache_condition(self.cache):
            self.flush_cache()
