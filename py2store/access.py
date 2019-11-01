"""
The logic to allow configurations (and defaults) to be parametrized by external environmental variables and files.

There are two main key-value stores: One for configurations the user wants to reuse, and the other for the user's
desired defaults. Both have the same structure:
    * first level key: Name of the resource (should be a valid python variable name)
    * The reminder is more or less free form (until the day we lay out some schemas for this)

The system will look for the specification of user_configs and user_defaults in a json file.
The filepath to this json file can specified in environment variables
    PY2STORE_CONFIGS_JSON_FILEPATH and PY2STORE_DEFAULTS_JSON_FILEPATH
respectively.
By default, they are:
    ~/.py2store_configs.json and ~/.py2store_defaults.json
respectively.
"""
import os
from warnings import warn
from py2store.util import DictAttr, str_to_var_str


def getenv(name, default=None):
    """Like os.getenv, but removes a suffix \\r character if present (problem with some env var systems)"""
    v = os.getenv(name, default)
    if v.endswith('\r'):
        return v[:-1]
    else:
        return v


user_configs_dict = {}
user_defaults_dict = {}
user_configs = None
user_defaults = None

try:
    import json

    user_configs_dirpath = os.path.expanduser(getenv('PY2STORE_CONFIGS_DIR', '~/.py2store_configs'))
    if os.path.isdir(user_configs_dirpath):
        def directory_json_items():
            for f in filter(lambda x: x.endswith('.json'), os.listdir(user_configs_dirpath)):
                filepath = os.path.join(user_configs_dirpath, f)
                name, _ = os.path.splitext(f)
                try:
                    d = json.load(open(filepath))
                    yield str_to_var_str(name), d
                except json.JSONDecodeError:
                    warn(f"This json file couldn't be json-decoded: {filepath}")
                except Exception:
                    warn(f"Unknown error when trying to json.load this file: {filepath}")


        user_configs = DictAttr(**{k: v for k, v in directory_json_items()})

    else:
        warn(f"The configs directory wasn't found (please make it): {user_configs_dirpath}")
        warn("Configs in a single json is being deprecated")
        user_configs_filepath = os.path.expanduser(getenv('PY2STORE_CONFIGS_JSON_FILEPATH', '~/.py2store_configs.json'))
        if os.path.isfile(user_configs_filepath):
            user_configs_dict = json.load(open(user_configs_filepath))
            user_configs = DictAttr(**{str_to_var_str(k): v for k, v in user_configs_dict.items()})

    user_defaults_filepath = os.path.expanduser(getenv('PY2STORE_DEFAULTS_JSON_FILEPATH', '~/.py2store_defaults.json'))
    if os.path.isfile(user_defaults_filepath):
        user_defaults_dict = json.load(open(user_defaults_filepath))
        user_defaults = DictAttr(**{str_to_var_str(k): v for k, v in user_defaults_dict.items()})

except Exception as e:
    warn(f"There was an exception when trying to get configs and defaults: {e}")
