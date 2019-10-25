import os

# Imports to be able to easily get started...
from py2store.stores.local_store import LocalStore, LocalBinaryStore, LocalTextStore
from py2store.stores.local_store import QuickStore, QuickBinaryStore, QuickTextStore
from py2store.base import Store
from py2store.trans import wrap_kvs
from py2store.access import user_configs_dict, user_configs, user_defaults_dict, user_defaults

file_sep = os.path.sep
