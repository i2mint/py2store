from functools import wraps, reduce


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


def mk_cached_store(caching_store, store_cls_you_want_to_cache):
    class CachedStore(store_cls_you_want_to_cache):
        _caching_store = caching_store

        @mk_memoizer(caching_store)
        def __getitem__(self, k):
            return super().__getitem__(k)

    return CachedStore


#
# def mk_cached_s3_store(local_cache_root, rootdir, rel_path_template, s3_resources=None):
#     local_cache = mk_a_nice_local_store(local_cache_root, rel_path_template)
#     rootdir, s3_resources = process_s3_resources(rootdir, s3_resources)
#
#     CachedWfStore = mk_cached_store(local_cache, NicerWfStore)
#
#     return CachedWfStore(
#         persister_class=S3BinaryStore,
#         persister_kwargs=s3_resources,
#         rootdir=rootdir, rel_path_template=rel_path_template,
#         naming_kwargs=DFLT_NAMING_KWARGS)


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


class WriteCache:
    """
    >>> store = dict()
    >>> cached_store = WriteCache(store, cache_to_kv=key_count)
    >>> # Adding 3 items...
    >>> cached_store.append(3)
    >>> cached_store.append('hi')
    >>> cached_store.append({'a': complex, 'obj': [1,2,3]})
    >>>
    >>> cached_store.cache  # The cache now has 3 items
    [3, 'hi', {'a': <class 'complex'>, 'obj': [1, 2, 3]}]
    >>> cached_store.store  # Store is still empty
    {}
    >>> # Flushing the items #############
    >>> cached_store.flush()
    >>> cached_store.cache  # The cache now has no more items
    []
    >>> cached_store.store  # But the store has them.
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

    def flush(self):
        for k, v in self.cache_to_kv(self.cache):
            self.store[k] = v
        self.cache = self._mk_cache()


class WriteCacheWithAutoFlush(WriteCache):
    def __init__(self, store, cache_to_kv=infinite_keycount_kvs, mk_cache=list,
                 flush_cache_condition=lambda x: len(x) > 0):
        super().__init__(store, cache_to_kv, mk_cache)
        self.flush_cache_condition = flush_cache_condition

    def __setitem__(self, k, v):
        super().__setitem__(k, v)
        if self.flush_cache_condition(self.cache):
            self.flush()

    def append(self, item):
        super().append(item)
        if self.flush_cache_condition(self.cache):
            self.flush()
