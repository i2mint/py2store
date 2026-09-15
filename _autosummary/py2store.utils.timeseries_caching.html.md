# py2store.utils.timeseries_caching

Tools to cache time-series data.

### Classes

| [`RegularTimeseriesCache`](#py2store.utils.timeseries_caching.RegularTimeseriesCache)([data_rate, ...])   | A type that pretends to be a (possibly very large) list, but where contents of the list are populated as they are needed.   |
|---------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|

### *class* py2store.utils.timeseries_caching.RegularTimeseriesCache(data_rate=1, time_rate=1, maxlen=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A type that pretends to be a (possibly very large) list, but where contents of the list are populated as they are
needed. Further, the indexing of the list can be overwritten for the convenience of the user.

The canonical application is where we have segments of continuous waveform indexed by utc microseconds timestamps.

It is convenient to be able to read segments of this waveform as if it was one big waveform (handling the
discontinuities gracefully), and have the choice of using (relative or absolute) integer indices or utc indices.
