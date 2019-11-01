import itertools
import time
from collections import defaultdict
from functools import reduce
from operator import add


def flush_on_exit(cls):
    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return self.flush_cache()

    new_cls = type(cls.__name__, (cls,), {})
    new_cls.__enter__ = __enter__
    new_cls.__exit__ = __exit__
    return new_cls


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


@flush_on_exit
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

    def extend(self, items):
        for item in items:
            self.append(item)

    def flush_cache(self):
        for k, v in self.cache_to_kv(self.cache):
            self.store[k] = v
        self.cache = self._mk_cache()

    def close(self):
        return self.flush_cache()


class CumulAggregWriteKvItems(CumulAggregWrite):
    def __init__(self, store):
        super().__init__(store, cache_to_kv=lambda gen: iter(gen), mk_cache=list)


def condition_flush_on_every_write(cache):
    """Boolean function used as flush_cache_condition to anytime the cache is non-empty"""
    return len(cache) > 0


class CumulAggregWriteWithAutoFlush(CumulAggregWrite):
    def __init__(self, store, cache_to_kv=infinite_keycount_kvs, mk_cache=list,
                 flush_cache_condition=condition_flush_on_every_write):
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
