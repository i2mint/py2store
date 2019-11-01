from itertools import islice
from collections.abc import Mapping


class iSliceStore(Mapping):
    """
    Wraps a store to make a reader that acts as if the store was a list (with integer keys, and that can be sliced).
    I say "list", but it should be noted that the behavior is more that of range, that outputs an element of the list
    when keying with an integer, but returns an iterable object (a range) if sliced.

    Here, a map object is returned when the sliceable store is sliced.

    >>> s = {'foo': 'bar', 'hello': 'world', 'alice': 'bob'}
    >>> sliceable_s = iSliceStore(s)
    >>> sliceable_s[1]
    'world'
    >>> list(sliceable_s[0:2])
    ['bar', 'world']
    >>> list(sliceable_s[-2:])
    ['world', 'bob']
    >>> list(sliceable_s[:-1])
    ['bar', 'world']
    """
    def __init__(self, store):
        self.store = store

    def _get_key(self, k):
        return next(islice(self.store.keys(), k, k + 1))

    def _get_keys(self, k):
        start, stop, step = k.start, k.stop, k.step
        assert (step is None) or (step > 0), "step of slice can't be negative"

        negative_start = start is not None and start < 0
        negative_stop = stop is not None and stop < 0
        if negative_start or negative_stop:
            n = self.__len__()
            if negative_start:
                start = n + start
            if negative_stop:
                stop = n + stop

        return islice(self.store.keys(), start, stop, step)

    def __getitem__(self, k):
        if not isinstance(k, slice):
            _id = next(islice(self.store.keys(), k, k + 1))
            return self.store[self._get_key(k)]
        else:
            return map(self.store.__getitem__, self._get_keys(k))

    def __iter__(self):
        return self.store.__iter__()

    def __len__(self):
        return self.store.__len__()