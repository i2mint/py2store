import os
import json
import pickle
import csv
from io import StringIO, BytesIO


def csv_fileobj(csv_data, *args, **kwargs):  # TODO: Use extended wraps func to inject
    fp = StringIO('')
    writer = csv.writer(fp)
    writer.writerows(csv_data, *args, **kwargs)
    fp.seek(0)
    return fp.read().encode()


def identity_method(x):
    return x


dflt_func_key = lambda self, k: os.path.splitext(k)[1]
dflt_dflt_incoming_val_trans = staticmethod(identity_method)

dflt_incoming_val_trans_for_key = {
    '.bin': identity_method,
    '.csv': lambda v: list(csv.reader(StringIO(v.decode()))),
    '.txt': lambda v: v.decode(),
    '.pkl': lambda v: pickle.loads(v),
    '.pickle': lambda v: pickle.loads(v),
    '.json': lambda v: json.loads(v),
}

dflt_outgoing_val_trans_for_key = {
    '.bin': identity_method,
    '.csv': csv_fileobj,
    '.txt': lambda v: v.encode(),
    '.pkl': lambda v: pickle.dumps(v),
    '.pickle': lambda v: pickle.dumps(v),
    '.json': lambda v: json.dumps(v),
}


class MiscReaderMixin:
    """Mixin to transform incoming vals according to the key their under.
    Warning: If used as a subclass, this mixin should (in general) be placed before the store


    >>> # make a reader that will wrap a dict
    >>> class MiscReader(MiscReaderMixin, dict):
    ...     def __init__(self, d,
    ...                         incoming_val_trans_for_key=None,
    ...                         dflt_incoming_val_trans=None,
    ...                         func_key=None):
    ...         dict.__init__(self, d)
    ...         MiscReaderMixin.__init__(self, incoming_val_trans_for_key, dflt_incoming_val_trans, func_key)
    ...
    >>>
    >>> incoming_val_trans_for_key = dict(
    ...     MiscReaderMixin._incoming_val_trans_for_key,  # take the existing defaults...
    ...     **{'.bin': lambda v: [ord(x) for x in v.decode()], # ... override how to handle the .bin extension
    ...      '.reverse_this': lambda v: v[::-1]  # add a new extension (and how to handle it)
    ...     })
    >>>
    >>> import pickle
    >>> d = {
    ...     'a.bin': b'abc123',
    ...     'a.reverse_this': b'abc123',
    ...     'a.csv': b'event,year\\n Magna Carta,1215\\n Guido,1956',
    ...     'a.txt': b'this is not a text',
    ...     'a.pkl': pickle.dumps(['text', [str, map], {'a list': [1, 2, 3]}]),
    ...     'a.json': '{"str": "field", "int": 42, "float": 3.14, "array": [1, 2], "nested": {"a": 1, "b": 2}}',
    ... }
    >>>
    >>> s = MiscReader(d=d, incoming_val_trans_for_key=incoming_val_trans_for_key)
    >>> list(s)
    ['a.bin', 'a.reverse_this', 'a.csv', 'a.txt', 'a.pkl', 'a.json']
    >>> s['a.bin']
    [97, 98, 99, 49, 50, 51]
    >>> s['a.reverse_this']
    b'321cba'
    >>> s['a.csv']
    [['event', 'year'], [' Magna Carta', '1215'], [' Guido', '1956']]
    >>> s['a.pkl']
    ['text', [<class 'str'>, <class 'map'>], {'a list': [1, 2, 3]}]
    >>> s['a.json']
    {'str': 'field', 'int': 42, 'float': 3.14, 'array': [1, 2], 'nested': {'a': 1, 'b': 2}}
    """

    _func_key = lambda self, k: os.path.splitext(k)[1]
    _dflt_incoming_val_trans = staticmethod(identity_method)

    _incoming_val_trans_for_key = dflt_incoming_val_trans_for_key

    def __init__(self, incoming_val_trans_for_key=None,
                 dflt_incoming_val_trans=None,
                 func_key=None):
        if incoming_val_trans_for_key is not None:
            self._incoming_val_trans_for_key = incoming_val_trans_for_key
        if dflt_incoming_val_trans is not None:
            self._dflt_incoming_val_trans = dflt_incoming_val_trans
        if func_key is not None:
            self._func_key = func_key

    def __getitem__(self, k):
        func_key = self._func_key(k)
        trans_func = self._incoming_val_trans_for_key.get(func_key, self._dflt_incoming_val_trans)
        return trans_func(super().__getitem__(k))


class MiscStoreMixin(MiscReaderMixin):
    """Mixin to transform incoming and outgoing vals according to the key their under.
    Warning: If used as a subclass, this mixin should (in general) be placed before the store

    >>> # Make a class to wrap a dict with a layer that transforms written and read values
    >>> class MiscStore(MiscStoreMixin, dict):
    ...     def __init__(self, d,
    ...                         incoming_val_trans_for_key=None, outgoing_val_trans_for_key=None,
    ...                         dflt_incoming_val_trans=None, dflt_outgoing_val_trans=None,
    ...                         func_key=None):
    ...         dict.__init__(self, d)
    ...         MiscStoreMixin.__init__(self, incoming_val_trans_for_key, outgoing_val_trans_for_key,
    ...                                 dflt_incoming_val_trans, dflt_outgoing_val_trans, func_key)
    ...
    >>>
    >>> outgoing_val_trans_for_key = dict(
    ...     MiscStoreMixin._outgoing_val_trans_for_key,  # take the existing defaults...
    ...     **{'.bin': lambda v: ''.join([chr(x) for x in v]).encode(), # ... override how to handle the .bin extension
    ...        '.reverse_this': lambda v: v[::-1]  # add a new extension (and how to handle it)
    ...     })
    >>> ss = MiscStore(d={},  # store starts empty
    ...                incoming_val_trans_for_key={},  # overriding incoming trans so we can see the raw data later
    ...                outgoing_val_trans_for_key=outgoing_val_trans_for_key)
    ...
    >>> # here's what we're going to write in the store
    >>> data_to_write = {
    ...      'a.bin': [97, 98, 99, 49, 50, 51],
    ...      'a.reverse_this': b'321cba',
    ...      'a.csv': [['event', 'year'], [' Magna Carta', '1215'], [' Guido', '1956']],
    ...      'a.txt': 'this is not a text',
    ...      'a.pkl': ['text', [str, map], {'a list': [1, 2, 3]}],
    ...      'a.json': {'str': 'field', 'int': 42, 'float': 3.14, 'array': [1, 2], 'nested': {'a': 1, 'b': 2}}}
    >>> # write this data in our store
    >>> for k, v in data_to_write.items():
    ...     ss[k] = v
    >>> list(ss)
    ['a.bin', 'a.reverse_this', 'a.csv', 'a.txt', 'a.pkl', 'a.json']
    >>> # Looking at the contents (what was actually stored/written)
    >>> for k, v in ss.items():
    ...     if k != 'a.pkl':
    ...         print(f"{k}: {v}")
    ...     else:  # need to verify pickle data differently, since printing contents is problematic in doctest
    ...         assert pickle.loads(v) == data_to_write['a.pkl']
    a.bin: b'abc123'
    a.reverse_this: b'abc123'
    a.csv: b'event,year\\r\\n Magna Carta,1215\\r\\n Guido,1956\\r\\n'
    a.txt: b'this is not a text'
    a.json: {"str": "field", "int": 42, "float": 3.14, "array": [1, 2], "nested": {"a": 1, "b": 2}}
    """
    _dflt_outgoing_val_trans_for_key = staticmethod(identity_method)
    _outgoing_val_trans_for_key = dflt_outgoing_val_trans_for_key

    def __init__(self, incoming_val_trans_for_key=None,
                 outgoing_val_trans_for_key=None,
                 dflt_incoming_val_trans=None,
                 dflt_outgoing_val_trans=None,
                 func_key=None):
        super().__init__(incoming_val_trans_for_key, dflt_incoming_val_trans, func_key)
        if outgoing_val_trans_for_key is not None:
            self._outgoing_val_trans_for_key = outgoing_val_trans_for_key
        if dflt_outgoing_val_trans is not None:
            self._dflt_outgoing_val_trans = dflt_outgoing_val_trans

    def __setitem__(self, k, v):
        func_key = self._func_key(k)
        trans_func = self._outgoing_val_trans_for_key.get(func_key, self._dflt_outgoing_val_trans_for_key)
        return super().__setitem__(k, trans_func(v))