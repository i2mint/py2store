"""

Needs python's redis package:
```
    pip install redis
```
Needs a redis server running.

To get/install Redis: https://redis.io/topics/quickstart

To launch local redis service.
```
    redis-server
```
"""
from py2store.base import Collection, KvReader, KvPersister
from py2store.util import ModuleNotFoundErrorNiceMessage
from functools import wraps


class RedisType:
    string = b"string"
    list = b"list"


with ModuleNotFoundErrorNiceMessage():
    from redis import Redis


class RedisFactories:
    @classmethod
    def from_source(cls, source):
        """Makes an instance initialized with attribute '_source' from given source"""
        self = object.__new__(cls)
        self._source = source
        return self

    @classmethod
    def from_sourced_object(cls, obj):
        """Makes a instance initialized with '_source' taken from obj._source (existence assumed)"""
        return cls.from_source(obj._source)


# TODO: Check:
#   Redis object seems to have getitem, setitem and delitem, so might already have Mapping API


class RedisBytesCollection(Collection, RedisFactories):
    @wraps(Redis.__init__)
    def __init__(self, **kwargs):
        self._source = Redis(**kwargs)

    def __iter__(self):
        yield from self._source.keys()

    def __getitem__(self, k):
        return self._source.get(k)

    def __contains__(self, k):
        return k in self._source

    def __len__(self):
        return len(self._source.keys())  # TODO: Any source method for this?


class RedisBytesReader(RedisBytesCollection, KvReader):
    def __getitem__(self, k):
        return self._source.get(k)


class RedisBytesPersister(RedisBytesReader, KvPersister):
    """
    Provides a `collections.abc.MutableMapping` (i.e. dict-like) interface to Redis.

    Note that Redis automatically converts everything to bytes when writing, which means that
    read and write are not inverse of each other in the base RedisPersister.
    A serialization/deserialization layer can be added to make read and write consistent.

    >>> s = RedisBytesPersister()  # plenty of params possible (all those of redis.Redis), but taking defaults.
    >>>
    >>> # clear the kehys we'll be using
    >>> keys = ['_pyst_test_str', '_pyst_test_int', '_pyst_test_float']
    >>> for k in keys:
    ...     del s[k]
    >>>
    >>> before_length = len(s)
    >>>
    >>> s['_pyst_test_str'] = 'hello'
    >>> s['_pyst_test_str']  # note you won't be getting a str but bytes
    b'hello'
    >>>
    >>> '_pyst_test_str' in s
    >>>
    >>> # numbers are converted to strings then bytes
    >>> s['_pyst_test_int'] = 42
    >>> assert s['_pyst_test_int'] == b'42'
    >>> s['_pyst_test_float'] = 3.14
    >>> assert s['_pyst_test_float'] == b'3.14'
    >>>
    >>> assert len(s) == before_length + 3
    >>>
    >>> '_pyst_test_float' in
    >>>
    >>> # clean up
    >>> for k in keys:
    ...     del s[k]
    >>>
    """

    write_kwargs = dict(ex=None, px=None, nx=False, xx=False, keepttl=False)

    def __setitem__(self, k, v):
        # TODO: Extend to a store that can handle some basic python types (lists, ints, floats)
        return self._source.set(k, v, **self.write_kwargs)

    def __delitem__(self, k):
        return self._source.__delitem__(k)


# TODO: Make py2store types to handle Redis value types in a consistent matter
"""Type	Commands
Sets	SADD, SCARD, SDIFF, SDIFFSTORE, SINTER, SINTERSTORE, SISMEMBER, SMEMBERS, SMOVE, 
        SPOP, SRANDMEMBER, SREM, SSCAN, SUNION, SUNIONSTORE
Hashes	HDEL, HEXISTS, HGET, HGETALL, HINCRBY, HINCRBYFLOAT, HKEYS, HLEN, HMGET, 
        HMSET, HSCAN, HSET, HSETNX, HSTRLEN, HVALS
Lists	BLPOP, BRPOP, BRPOPLPUSH, LINDEX, LINSERT, LLEN, LPOP, LPUSH, LPUSHX, LRANGE, 
        LREM, LSET, LTRIM, RPOP, RPOPLPUSH, RPUSH, RPUSHX
Strings	APPEND, BITCOUNT, BITFIELD, BITOP, BITPOS, DECR, DECRBY, GET, GETBIT, GETRANGE, GETSET, 
        INCR, INCRBY, INCRBYFLOAT, MGET, MSET, MSETNX, PSETEX, SET, SETBIT, SETEX, SETNX, 
        SETRANGE, STRLEN
"""

"""See 729 - py2store - Redis note book to see how to generate the following:
lset: (self, name, index, value)
	Set ``position`` of list ``name`` to ``value``...
lrange: (self, name, start, end)
	Return a slice of the list ``name`` between...
lpush: (self, name, *values)
	Push ``values`` onto the head of the list ``name``...
lrem: (self, name, count, value)
	Remove the first ``count`` occurrences of elements equal to ``value``...
ltrim: (self, name, start, end)
	Trim the list ``name``, removing all values not within the slice...
lpop: (self, name)
	Remove and return the first item of the list ``name``...
llen: (self, name)
	Return the length of the list ``name``...
lpushx: (self, name, value)
	Push ``value`` onto the head of the list ``name`` if ``name`` exists...
linsert: (self, name, where, refvalue, value)
	Insert ``value`` in list ``name`` either immediately before or after...
lindex: (self, name, index)
	Return the item from list ``name`` at position ``index``...
	
rpush: (self, name, *values)
	Push ``values`` onto the tail of the list ``name``...
rpushx: (self, name, value)
	Push ``value`` onto the tail of the list ``name`` if ``name`` exists...
rpop: (self, name)
	Remove and return the last item of the list ``name``...
rpoplpush: (self, src, dst)
	RPOP a value off of the ``src`` list and atomically LPUSH it...
	
blpop: (self, keys, timeout=0)
	LPOP a value off of the first non-empty list...
brpop: (self, keys, timeout=0)
	RPOP a value off of the first non-empty list...
brpoplpush: (self, src, dst, timeout=0)
	Pop a value off the tail of ``src``, push it on the head of ``dst``...
"""

from collections.abc import MutableSequence


# TODO: Redis list type is more of a linked-list than a list. Better subclass deque?
class RedisList(MutableSequence):
    """
    An object to operate on Redis lists as if they were python lists
    """

    def __init__(self, source, name):
        self._source = source
        self._name = name

    def __len__(self):
        return self._source.llen(self._name)

    def __getitem__(self, i):
        if isinstance(i, int):
            return self._source.lindex(self._name, i)
        else:  # assume it's a slice, and modify it to conform to inclusive Redis slicing
            try:
                if i.step is not None:
                    raise NotImplementedError(
                        "Slicing is so far only implemented without step"
                    )
                return self._source.lrange(
                    self._name, i.start or 0, i.stop - 1
                )
            except AttributeError:
                raise KeyError(
                    f"Index should be an integer or a slice object. Was {i}"
                )

    def __iter__(self):
        # TODO: Find a more efficient way to do this.
        #   In batches perhaps? But what's the optimal batch size?
        #   async fetching of the next value/batch while yielding the one that's already fetched?
        for i in range(len(self)):
            yield self[i]

    def __setitem__(self, i, v):
        return self._source.lset(self._name, i, v)

    def __delitem__(self, i):  # TODO: Implement
        raise NotImplementedError(
            "Don't know how to (efficiently/directly) delete a single middle item."
        )

    def append(self, v):
        return self._source.rpushx(self._name, v)

    def extend(self, iterable):
        self._source.rpush(self._name, *iterable)

    def insert(self, i, v):  # TODO: Implement
        raise NotImplementedError("Might have to do with self._source.linsert")


# TODO: Consider if should move to stores
# The following will probably be moved to stores, since it has serialization and indexinig logic
class RedisCollection(RedisBytesCollection):
    def __getitem__(self, k):
        val_type = self._source.type(k)
        if val_type == b"string":
            return self._source.get(k)
        elif val_type == b"list":
            return RedisList(self._source, k)


from typing import Iterable
from collections.abc import Mapping


class RedisPersister(RedisCollection, RedisBytesPersister):
    def __setitem__(self, k, v):
        if isinstance(v, (str, bytes)):
            return super().__setitem__(k, v)
        elif isinstance(v, Iterable):
            if k in self:
                del self[k]
            return self._source.rpush(k, *v)
