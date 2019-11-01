import os
from py2store.util import ModuleNotFoundIgnore

file_sep = os.path.sep

# Imports to be able to easily get started...
from py2store.base import KvCollection, KvReader, KvPersister, Reader, Persister
from py2store.stores.local_store import LocalStore, LocalBinaryStore, LocalTextStore, PickleStore
from py2store.stores.local_store import QuickStore, QuickBinaryStore, QuickTextStore, QuickJsonStore, QuickPickleStore
from py2store.base import Store
from py2store.trans import wrap_kvs
from py2store.access import user_configs_dict, user_configs, user_defaults_dict, user_defaults

with ModuleNotFoundIgnore():
    from py2store.stores.s3_store import S3BinaryStore, S3TextStore, S3PickleStore
with ModuleNotFoundIgnore():
    from py2store.stores.mongo_store import MongoStore, MongoTupleKeyStore, MongoAnyKeyStore
