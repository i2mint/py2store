import pickle
import marshal
from functools import partial

rw_funcs_maker_for = dict()


# TODO: Make (in a different module) a factory to encapsulate the common pattern of the next three functions, and others

def mk_pickle_rw_funcs(fix_imports=True, protocol=None, pickle_encoding='ASCII', pickle_errors='strict'):
    """Generates a reader and writer using pickle. That is, a pair of parametrized loads and dumps

    >>> read, write = mk_pickle_rw_funcs()
    >>> d = {'a': 'simple', 'and': {'a': b'more', 'complex': [1, 2.2, dict]}}
    >>> serialized_d = write(d)
    >>> deserialized_d = read(serialized_d)
    >>> assert d == deserialized_d
    """
    return (
        partial(pickle.loads, fix_imports=fix_imports, encoding=pickle_encoding, errors=pickle_errors),
        partial(pickle.dumps, protocol=protocol, fix_imports=fix_imports)
    )


rw_funcs_maker_for['pickle'] = mk_pickle_rw_funcs


def mk_marshal_rw_funcs(**kwargs):  # TODO: Check actual arguments for marshal load and dump
    """Generates a reader and writer using marshal. That is, a pair of parametrized loads and dumps

    >>> read, write = mk_marshal_rw_funcs()
    >>> d = {'a': 'simple', 'and': {'a': b'more', 'complex': [1, 2.2, dict]}}
    >>> serialized_d = write(d)
    >>> deserialized_d = read(serialized_d)
    >>> assert d == deserialized_d
    """
    return (
        partial(marshal.loads, **kwargs),
        partial(marshal.dumps, **kwargs)
    )


rw_funcs_maker_for['marshal'] = mk_marshal_rw_funcs

##### Extras (requiring some third-party packages ######################################################################

from py2store.util import ModuleNotFoundIgnore

with ModuleNotFoundIgnore():
    import dill


    def mk_dill_rw_funcs(ignore=None, protocol=None, byref=None, fmode=None, recurse=None):
        """Generates a reader and writer using dill. That is, a pair of parametrized loads and dumps

        >>> read, write = mk_dill_rw_funcs()
        >>> d = {'a': 'simple', 'and': {'a': b'more', 'complex': [1, 2.2, dict]}}
        >>> serialized_d = write(d)
        >>> deserialized_d = read(serialized_d)
        >>> assert d == deserialized_d
        """

        return (
            partial(dill.loads, ignore=ignore),
            partial(dill.dumps, protocol=protocol, byref=byref, fmode=fmode, recurse=recurse)
        )


    rw_funcs_maker_for['dill'] = mk_dill_rw_funcs

# class PickleMixin:
#     """Local files store with pickle serialization"""
#
#     def __init__(self, path_format,
#                  fix_imports=True, protocol=None, pickle_encoding='ASCII', pickle_errors='strict',
#                  **open_kwargs):
#         super().__init__(path_format, mode='b', **open_kwargs)
#         self._loads = partial(pickle.loads, fix_imports=fix_imports, encoding=pickle_encoding, errors=pickle_errors)
#         self._dumps = partial(pickle.dumps, protocol=protocol, fix_imports=fix_imports)
#
#     def __getitem__(self, k):
#         return self._loads(super().__getitem__(k))
#
#     def __setitem__(self, k, v):
#         return super().__setitem__(k, self._dumps(v))
