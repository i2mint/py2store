import os

# Imports to be able to easily get started...
from py2store.stores.local_store import LocalStore, LocalBinaryStore, LocalTextStore
from py2store.stores.local_store import QuickStore, QuickBinaryStore, QuickTextStore
from py2store.base import Store

file_sep = os.path.sep


def getenv(name, default=None):
    """Like os.getenv, but removes a suffix \\r character if present (problem with some env var systems)"""
    v = os.getenv(name, default)
    if v.endswith('\r'):
        return v[:-1]
    else:
        return v


user_configs = {}
user_defaults = {}

try:
    import json

    user_configs_filepath = os.path.expanduser(getenv('PY2STORE_CONFIGS_JSON_FILEPATH', '~/.py2store_configs.json'))
    if os.path.isfile(user_configs_filepath):
        user_configs = json.load(open(user_configs_filepath))

    user_defaults_filepath = os.path.expanduser(getenv('PY2STORE_DEFAULTS_JSON_FILEPATH', '~/.py2store_defaults.json'))
    if os.path.isfile(user_defaults_filepath):
        user_defaults = json.load(open(user_defaults_filepath))

except Exception as e:
    from warnings import warn

    warn(f"There was an exception when trying to get configs and defaults: {e}")
