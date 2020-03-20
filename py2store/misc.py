import os
import json
import pickle
import csv
from io import StringIO, BytesIO

from py2store import LocalBinaryStore
from py2store.util import imdict


def csv_fileobj(csv_data, *args, **kwargs):  # TODO: Use extended wraps func to inject
    fp = StringIO('')
    writer = csv.writer(fp)
    writer.writerows(csv_data, *args, **kwargs)
    fp.seek(0)
    return fp.read().encode()


def identity_method(x):
    return x


# TODO: Enhance default handling so users can have their own defaults (checking for local config file etc.)
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
    '.json': lambda v: json.dumps(v).encode(),
}


# TODO: Different misc objects (function, class, default instance) should be a aligned more

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

    _incoming_val_trans_for_key = imdict(dflt_incoming_val_trans_for_key)

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


# TODO: I'd really like to reuse MiscReaderMixin here! There's a lot of potential.
#  If store argument of get_obj was a type instead of an instance, or if MiscReaderMixin was a transformer, if would
#  be easier -- but would it make their individual concerns mixed?
def get_obj(k, store=LocalBinaryStore(path_format=''),
            incoming_val_trans_for_key=imdict(dflt_incoming_val_trans_for_key),
            dflt_incoming_val_trans=identity_method,
            func_key=lambda k: os.path.splitext(k)[1]):
    """A quick way to get an object, with default... everything (but the key, you know, a clue of what you want)"""

    trans_func = (incoming_val_trans_for_key or {}).get(func_key(k), dflt_incoming_val_trans)
    return trans_func(store[k])


# TODO: I'd really like to reuse MiscReaderMixin here! There's a lot of potential.
#  Same comment as above.
class MiscGetter:
    """
    An object to write (and only write) to a store (default local files) with automatic deserialization
    according to a property of the key (default: file extension).

    >>> from py2store.misc import get_obj, misc_objs_get
    >>> import os
    >>> import json
    >>>
    >>> pjoin = lambda *p: os.path.join(os.path.expanduser('~'), *p)
    >>> path = pjoin('tmp.json')
    >>> d = {'a': {'b': {'c': [1, 2, 3]}}}
    >>> json.dump(d, open(path, 'w'))  # putting a json file there, the normal way, so we can use it later
    >>>
    >>> k = path
    >>> t = get_obj(k)  # if you'd like to use a function
    >>> assert t == d
    >>> tt = misc_objs_get[k]  # if you'd like to use an object (note: can get, but nothing else (no list, set, del, etc))
    >>> assert tt == d
    >>> t
    {'a': {'b': {'c': [1, 2, 3]}}}
    """

    def __init__(self,
                 store=LocalBinaryStore(path_format=''),
                 incoming_val_trans_for_key=imdict(dflt_incoming_val_trans_for_key),
                 dflt_incoming_val_trans=identity_method,
                 func_key=lambda k: os.path.splitext(k)[1]):
        self.store = store
        self.incoming_val_trans_for_key = incoming_val_trans_for_key
        self.dflt_incoming_val_trans = dflt_incoming_val_trans
        self.func_key = func_key

    def __getitem__(self, k):
        return get_obj(k, self.store, self.incoming_val_trans_for_key, self.dflt_incoming_val_trans, self.func_key)


misc_objs_get = MiscGetter()

# TODO: Make this be more tightly couples with the actual default used in get_obj and MiscGetter (avoid misalignments)
misc_objs_get.dflt_incoming_val_trans_for_key = dflt_incoming_val_trans_for_key


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


# TODO: I'd really like to reuse MiscStoreMixin here! There's a lot of potential.
#  If store argument of get_obj was a type instead of an instance, or if MiscReaderMixin was a transformer, if would
#  be easier -- but would it make their individual concerns mixed?
def set_obj(k, v, store=LocalBinaryStore(path_format=''),
            outgoing_val_trans_for_key=imdict(dflt_outgoing_val_trans_for_key),
            func_key=lambda k: os.path.splitext(k)[1]):
    """A quick way to get an object, with default... everything (but the key, you know, a clue of what you want)"""

    trans_func = outgoing_val_trans_for_key.get(func_key(k), dflt_outgoing_val_trans_for_key)
    store[k] = trans_func(v)


# TODO: I'd really like to reuse MiscReaderMixin here! There's a lot of potential.
#  Same comment as above.
class MiscGetterAndSetter(MiscGetter):
    """
    An object to read and write (and nothing else) to a store (default local) with automatic (de)serialization
    according to a property of the key (default: file extension).
    >>> from py2store.misc import set_obj, misc_objs  # the function and the object
    >>> import json
    >>> import os
    >>>
    >>> pjoin = lambda *p: os.path.join(os.path.expanduser('~'), *p)
    >>>
    >>> d = {'a': {'b': {'c': [1, 2, 3]}}}
    >>> misc_objs[pjoin('tmp.json')] = d
    >>> assert misc_objs['/Users/twhalen/tmp.json'] == d  # yep, it's there, and can be retrieved
    >>> assert json.load(open('/Users/twhalen/tmp.json')) == d  # in case you don't believe it's an actual json file
    >>>
    >>> # using pickle
    ... misc_objs[pjoin('tmp.pkl')] = d
    >>> assert misc_objs[pjoin('tmp.pkl')] == d
    >>>
    >>> # using txt
    ... misc_objs[pjoin('tmp.txt')] = 'hello world!'
    >>> assert misc_objs[pjoin('tmp.txt')] == 'hello world!'
    >>>
    >>> # using csv
    ... misc_objs[pjoin('tmp.csv')] = [[1,2,3], ['a','b','c']]
    >>> assert misc_objs[pjoin('tmp.csv')] == [['1','2','3'], ['a','b','c']]  # yeah, well, not numbers, but you deal with it
    >>>
    >>> # using bin
    ... misc_objs[pjoin('tmp.bin')] = b'let us pretend these are bytes of an audio waveform'
    >>> assert misc_objs[pjoin('tmp.bin')] == b'let us pretend these are bytes of an audio waveform'

    """

    def __init__(self,
                 store=LocalBinaryStore(path_format=''),
                 incoming_val_trans_for_key=imdict(dflt_incoming_val_trans_for_key),
                 outgoing_val_trans_for_key=imdict(dflt_outgoing_val_trans_for_key),
                 dflt_incoming_val_trans=identity_method,
                 func_key=lambda k: os.path.splitext(k)[1]):
        self.store = store
        self.incoming_val_trans_for_key = incoming_val_trans_for_key
        self.outgoing_val_trans_for_key = outgoing_val_trans_for_key
        self.dflt_incoming_val_trans = dflt_incoming_val_trans
        self.func_key = func_key

    def __setitem__(self, k, v):
        return set_obj(k, v, self.store, self.outgoing_val_trans_for_key, self.func_key)


misc_objs = MiscGetterAndSetter()
