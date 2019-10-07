import os

# Imports to be able to easily get started...
from py2store.stores.local_store import LocalStore, LocalBinaryStore, LocalTextStore
from py2store.stores.local_store import QuickStore, QuickBinaryStore, QuickTextStore
from py2store.base import Store

file_sep = os.path.sep

user_configs = {}
user_defaults = {}

try:
    import json

    config_filepath = os.path.expanduser('~/.py2store_configs.json')
    if os.path.isfile(config_filepath):
        user_configs = json.load(open(config_filepath))

    defaults_filepath = os.path.expanduser('~/.py2store_defaults.json')
    if os.path.isfile(defaults_filepath):
        user_defaults = json.load(open(defaults_filepath))

except:
    pass
