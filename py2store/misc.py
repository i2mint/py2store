import os
import json
import pickle

from py2store import LocalBinaryStore


def identity_method(x):
    return x


dflt_func_key = lambda self, k: os.path.splitext(k)[1]
dflt_dflt_incoming_val_trans = staticmethod(identity_method)

dflt_incoming_val_trans_for_key = {
    '.bin': identity_method,
    '.txt': lambda v: v.decode(),
    '.pkl': lambda v: pickle.loads(v),
    '.pickle': lambda v: pickle.loads(v),
    '.json': lambda v: json.loads(v),
}

dflt_outgoing_val_trans_for_key = {
    '.bin': identity_method,
    '.txt': lambda v: v.encode(),
    '.pkl': lambda v: pickle.dumps(v),
    '.pickle': lambda v: pickle.dumps(v),
    '.json': lambda v: json.dumps(v),
}


class MiscReaderMixin:
    """Mixin to transform incoming vals in function of the key.
    Warning: If used as a subclass, this mixin should (in general) be placed before the store"""

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
    _dflt_outgoing_val_trans_for_key = staticmethod(identity_method)

    _outgoing_val_trans_for_key = dflt_outgoing_val_trans_for_key

    def __init__(self, incoming_val_trans_for_key=None,
                 outgoing_val_for_key=None,
                 dflt_incoming_val_trans=None,
                 dflt_outgoing_val_trans=None,
                 func_key=None):
        super().__init__(incoming_val_trans_for_key, dflt_incoming_val_trans, func_key)
        if outgoing_val_for_key is not None:
            self._outgoing_val_for_key = outgoing_val_for_key
        if dflt_outgoing_val_trans is not None:
            self._dflt_outgoing_val_trans = dflt_outgoing_val_trans

    def __setitem__(self, k, v):
        func_key = self._func_key(k)
        trans_func = self._outgoing_val_trans_for_key.get(func_key, self._dflt_outgoing_val_trans_for_key)
        return super().__setitem__(k, trans_func(v))
