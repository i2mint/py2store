import os
from py2store.util import ModuleNotFoundIgnore

file_sep = os.path.sep

# Imports to be able to easily get started...
from py2store.base import Collection, KvReader, KvPersister, Reader, Persister

from py2store.stores.local_store import LocalStore, LocalBinaryStore, LocalTextStore, LocalPickleStore, LocalJsonStore
from py2store.stores.local_store import QuickStore, QuickBinaryStore, QuickTextStore, QuickJsonStore, QuickPickleStore

from py2store.misc import MiscGetter, MiscGetterAndSetter, misc_objs, misc_objs_get, get_obj, set_obj
from py2store.base import Store
from py2store.trans import wrap_kvs, disable_delitem, disable_setitem, mk_read_only, kv_wrap, cache_iter, filtered_iter
from py2store.access import user_configs_dict, user_configs, user_defaults_dict, user_defaults, mystores

from py2store.stores.local_store import PickleStore  # consider deprecating and use LocalPickleStore instead?
from py2store.persisters.local_files import ZipReader, FilesOfZip, ZipFilesReader

with ModuleNotFoundIgnore():
    from py2store.stores.s3_store import S3BinaryStore, S3TextStore, S3PickleStore
with ModuleNotFoundIgnore():
    from py2store.stores.mongo_store import MongoStore, MongoTupleKeyStore, MongoAnyKeyStore


def kvhead(store):
    """Get the first item of a kv store"""
    for k in store:
        return k, store[k]


def ihead(store):
    """Get the first item of an iterable"""
    for item in store:
        return item
