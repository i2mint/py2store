# py2store.utils.cumul_aggreg_write

utils for bulk writing – accumulate, aggregate and write when some condition is met

### Functions

| [`condition_flush_on_every_write`](#py2store.utils.cumul_aggreg_write.condition_flush_on_every_write)(cache)          | Boolean function used as flush_cache_condition to anytime the cache is non-empty                                              |
|-------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `flush_on_exit`(cls)                                                                            |                                                                                                                               |
| `infinite_keycount_kvs`(gen)                                                                    |                                                                                                                               |
| `join_byte_values_and_key_as_current_utc_milliseconds`(gen)                                     |                                                                                                                               |
| `join_string_values_and_key_as_current_utc_milliseconds`(gen)                                   |                                                                                                                               |
| `key_count`(gen[, start])                                                                       |                                                                                                                               |
| `let_through`(gen)                                                                              |                                                                                                                               |
| [`mk_group_aggregator`](#py2store.utils.cumul_aggreg_write.mk_group_aggregator)(item_to_kv[, ...])         | Make a generator transforming function that will (a) make a key for each given item, (b) group all items according to the key |
| [`mk_group_aggregator_with_key_func`](#py2store.utils.cumul_aggreg_write.mk_group_aggregator_with_key_func)(item_to_key) | Make a generator transforming function that will (a) make a key for each given item, (b) group all items according to the key |
| `mk_kv_from_keygen`([keygen])                                                                   |                                                                                                                               |

### Classes

| [`CumulAggregWrite`](#py2store.utils.cumul_aggreg_write.CumulAggregWrite)(store[, cache_to_kv, mk_cache])   |    |
|-----------------------------------------------------------------------------------------------------|----|
| [`CumulAggregWriteKvItems`](#py2store.utils.cumul_aggreg_write.CumulAggregWriteKvItems)(store)                     |    |
| [`CumulAggregWriteWithAutoFlush`](#py2store.utils.cumul_aggreg_write.CumulAggregWriteWithAutoFlush)(store[, ...])        |    |

### *class* py2store.utils.cumul_aggreg_write.CumulAggregWrite(store, cache_to_kv=<function mk_kv_from_keygen.<locals>.aggregate>, mk_cache=<class 'list'>)

Bases: [`CumulAggregWrite`](#py2store.utils.cumul_aggreg_write.CumulAggregWrite)

### *class* py2store.utils.cumul_aggreg_write.CumulAggregWriteKvItems(store)

Bases: [`CumulAggregWrite`](#py2store.utils.cumul_aggreg_write.CumulAggregWrite)

### *class* py2store.utils.cumul_aggreg_write.CumulAggregWriteWithAutoFlush(store, cache_to_kv=<function mk_kv_from_keygen.<locals>.aggregate>, mk_cache=<class 'list'>, flush_cache_condition=<function condition_flush_on_every_write>)

Bases: [`CumulAggregWrite`](#py2store.utils.cumul_aggreg_write.CumulAggregWrite)

### py2store.utils.cumul_aggreg_write.condition_flush_on_every_write(cache)

Boolean function used as flush_cache_condition to anytime the cache is non-empty

### py2store.utils.cumul_aggreg_write.mk_group_aggregator(item_to_kv, aggregator_op=<built-in function add>, initial=<py2store.utils.cumul_aggreg_write.NoInitial object>)

Make a generator transforming function that will
(a) make a key for each given item,
(b) group all items according to the key

* **Parameters:**
  * **item_to_kv** – Function taking an item and returning the `(key, value)` pair to group by key.
  * **aggregator_op** – The aggregation binary function that is used to aggregate two items together.
    The function is used as is by the functools.reduce, applied to the sequence of items that were collected for
    a given group
  * **initial** – The “empty” element to start the reduce (aggregation) with, if necessary.
* **Returns:**
  A function taking an iterable of items and yielding `(key, aggregate)` pairs, one per key.

```pycon
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
```

### py2store.utils.cumul_aggreg_write.mk_group_aggregator_with_key_func(item_to_key, aggregator_op=<built-in function add>, initial=<py2store.utils.cumul_aggreg_write.NoInitial object>)

Make a generator transforming function that will
(a) make a key for each given item,
(b) group all items according to the key

* **Parameters:**
  * **item_to_key** – Function that takes an item of the generator and outputs the key that should be used to group items
  * **aggregator_op** – The aggregation binary function that is used to aggregate two items together.
    The function is used as is by the functools.reduce, applied to the sequence of items that were collected for
    a given group
  * **initial** – The “empty” element to start the reduce (aggregation) with, if necessary.
* **Returns:**
  A function taking an iterable of items and yielding `(key, aggregate)` pairs, one per key.

```pycon
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
```
