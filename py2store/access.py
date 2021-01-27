"""
Utils to load stores from store specifications.
Includes the logic to allow configurations (and defaults) to be parametrized by external environmental
variables and files.

Every data-sourced problem has it's problem-relevant stores. Once you get your stores right, along with the
right access credentials, indexing, serialization, caching, filtering etc. you'd like to be able to name, save
and/or share this specification, and easily get access to it later on.

Here are tools to help you out.

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
import importlib
from warnings import warn
from functools import reduce
from operator import getitem
from py2store.util import str_to_var_str
from py2store.sources import DictAttr

FAK = "$fak"


# TODO: Make a config_utils.py module to centralize config tools (configs for access is just one -- serializers another)
# TODO: Integrate (external because not standard lib) other safer tools for secrets, such as:
#  https://github.com/SimpleLegal/pocket_protector


def getenv(name, default=None):
    """Like os.getenv, but removes a suffix \\r character if present (problem with some env var systems)"""
    v = os.getenv(name, default)
    if v.endswith("\r"):
        return v[:-1]
    else:
        return v


def assert_callable(f: callable) -> callable:
    assert callable(f), f"Is not callable: {f}"
    return f


def dotpath_to_obj(dotpath):
    """Loads and returns the object referenced by the string DOTPATH_TO_MODULE.OBJ_NAME"""
    *module_path, obj_name = dotpath.split(".")
    if len(module_path) > 0:
        return getattr(
            importlib.import_module(".".join(module_path)), obj_name
        )
    else:
        return importlib.import_module(obj_name)


def dotpath_to_func(f: (str, callable)) -> callable:
    """Loads and returns the function referenced by f,
    which could be a callable or a DOTPATH_TO_MODULE.FUNC_NAME dotpath string to one.
    """

    if isinstance(f, str):
        if "." in f:
            *module_path, func_name = f.split(".")
            f = getattr(
                importlib.import_module(".".join(module_path)), func_name
            )
        else:
            f = getattr(importlib.import_module("py2store"), f)

    return assert_callable(f)


def compose(*functions):
    """Make a function that is the composition of the input functions"""
    return reduce(lambda f, g: lambda x: f(g(x)), functions, lambda x: x)


def dflt_func_loader(f) -> callable:
    """Loads and returns the function referenced by f,
    which could be a callable or a DOTPATH_TO_MODULE.FUNC_NAME dotpath string to one, or a pipeline of these
    """
    if isinstance(f, str) or callable(f):
        return dotpath_to_func(f)
    else:
        return compose(*map(dflt_func_loader, f))


def _fakit(f: callable, a: (tuple, list), k: dict):
    return f(*(a or ()), **(k or {}))


def fakit_from_dict(d, func_loader=assert_callable):
    return _fakit(func_loader(d["f"]), a=d.get("a", ()), k=d.get("k", {}))


def fakit_from_tuple(
        t: (tuple, list), func_loader: callable = dflt_func_loader
):
    f = func_loader(t[0])
    a = ()
    k = {}
    assert len(t) in {
        1,
        2,
        3,
    }, "A tuple fak must be of length 1, 2, or 3. No more, no less."
    if len(t) > 1:
        if isinstance(t[1], dict):
            k = t[1]
        else:
            assert isinstance(
                t[1], (tuple, list)
            ), "argument specs should be dict, tuple, or list"
            a = t[1]
        if len(t) > 2:
            if isinstance(t[2], dict):
                assert not k, "can only have one kwargs"
                k = t[2]
            else:
                assert isinstance(
                    t[2], (tuple, list)
                ), "argument specs should be dict, tuple, or list"
                assert not a, "can only have one args"
                a = t[2]
    return _fakit(f, a, k)


def fakit(fak, func_loader=dflt_func_loader):
    """Execute a fak with given f, a, k and function loader.

    Essentially returns func_loader(f)(*a, **k)

    Args:
        fak: A (f, a, k) specification. Could be a tuple or a dict (with 'f', 'a', 'k' keys). All but f are optional.
        func_loader: A function returning a function. This is where you specify any validation of func specification f,
            and/or how to get a callable from it.

    Returns: A python object.
    """

    if isinstance(fak, dict):
        return fakit_from_dict(fak, func_loader=func_loader)
    else:
        assert isinstance(
            fak, (tuple, list)
        ), "fak should be dict, tuple, or list"
        return fakit_from_tuple(fak, func_loader=func_loader)


fakit.from_dict = fakit_from_dict
fakit.from_tuple = fakit_from_tuple

user_configs_dict = {}
user_defaults_dict = {}
user_configs = None
user_defaults = None
mystores = None

try:
    import json

    user_configs_dirpath = os.path.expanduser(
        getenv("PY2STORE_CONFIGS_DIR", "~/.py2store_configs")
    )
    my_configs_dirname = os.path.expanduser(
        getenv("MY_PY2STORE_DIR_NAME", "my")
    )
    myconfigs_dirpath = os.path.join(user_configs_dirpath, my_configs_dirname)

    if os.path.isdir(user_configs_dirpath):

        def directory_json_items():
            for f in filter(
                    lambda x: x.endswith(".json"), os.listdir(user_configs_dirpath)
            ):
                filepath = os.path.join(user_configs_dirpath, f)
                name, _ = os.path.splitext(f)
                try:
                    d = json.load(open(filepath))
                    yield str_to_var_str(name), d
                except json.JSONDecodeError:
                    warn(
                        f"This json file couldn't be json-decoded: {filepath}"
                    )
                except Exception:
                    warn(
                        f"Unknown error when trying to json.load this file: {filepath}"
                    )


        user_configs = DictAttr(**{k: v for k, v in directory_json_items()})

        from py2store.base import KvStore
        from py2store.stores.local_store import (
            LocalJsonStore,
            LocalBinaryStore,
        )
        from py2store.trans import wrap_kvs
        from py2store.misc import MiscStoreMixin
        from functools import wraps

        if os.path.isdir(myconfigs_dirpath):
            from py2store.mixins import OverWritesNotAllowedMixin


            @OverWritesNotAllowedMixin.wrap
            class MyConfigs(MiscStoreMixin, LocalBinaryStore):
                key_sep = ':'

                @wraps(LocalBinaryStore)
                def __init__(self, *args, **kwargs):
                    LocalBinaryStore.__init__(self, *args, **kwargs)
                    self._init_args_kwargs = (args, kwargs)
                    if len(args) > 0:
                        self.dirpath = args[0]
                    elif len(kwargs) > 0:
                        self.dirpath = kwargs[next(iter(kwargs))]

                def refresh(self):
                    """Sometimes you add a file, and you want to make sure your myconfigs sees it.
                    refresh() does that for you. It reinitializes the reader."""
                    args, kwargs = self._init_args_kwargs
                    self.__init__(*args, **kwargs)

                def get(self, k):
                    v = super().get(k, None)
                    if v is None:
                        from warnings import warn

                        warn(
                            f"""You don't have the config file I'm expecting, so you'll have to enter it manually.
                        I'm expecting this filepath:\n\t {os.path.join(self.dirpath, k)}
                        """
                        )
                    return v

                def __getitem__(self, k):
                    try:
                        if self.key_sep not in k:
                            return super().__getitem__(k)
                        else:
                            return reduce(getitem, k.split(self.key_sep), self)
                    except KeyError:
                        raise KeyError(f"The '{k}' key wasn't found. "
                                       f"What this probably is, is that you need "
                                       f"a file named '{k}' in your {self.dirpath} folder. Do that and try again.")

                def get_config_value(self, k, path=None):
                    v = self.get(k)
                    if path is None:
                        return v
                    else:
                        if path in v:
                            return v[path]
                        else:
                            raise KeyError(f"I don't see any {path} in {k}")

                @property
                def rootdir(self):
                    return self._prefix

                def __delitem__(self, k):
                    raise NotImplementedError(
                        "Deletion was disabled. "
                        "MyConfigs wants to keep your configs safe, so if you want to delete this config, "
                        "do it another way (like manually)."
                    )


            myconfigs = MyConfigs(myconfigs_dirpath)
            myconfigs.dirpath = myconfigs_dirpath
        else:
            warn(
                f"""The py2store-myconfigs directory wasn't found: {myconfigs_dirpath}
            If you want to have all the cool functionality of `myconfigs`, you should make this directory, 
            and put stuff in it. Here's to make it easy for you to do it. Go to a terminal and run this:
                mkdir {myconfigs_dirpath}
            """
            )


        class MyStores(KvStore):
            func_loader = staticmethod(dflt_func_loader)

            def _obj_of_data(self, data):
                if FAK in data:
                    return fakit(data[FAK], self.func_loader)
                else:
                    msg = "Case not handled by MyStores"
                    if isinstance(data, dict):
                        raise ValueError(f"{msg}: keys: {list(data.keys())}")
                    else:
                        raise ValueError(f"{msg}: type: {type(data)}")

            @property
            def configs(self):
                return self.store


        def without_json_ext(_id):
            assert _id.endswith(".json"), "Should end with .json"
            return _id[: -len(".json")]


        def add_json_ext(k):
            return k + ".json"


        ExtLessJsonStore = wrap_kvs(
            LocalJsonStore,
            name="ExtLessJsonStore",
            key_of_id=without_json_ext,
            id_of_key=add_json_ext,
        )

        stores_json_path_format = os.path.join(
            user_configs_dirpath, "stores", "json", "{}.json"
        )
        mystores = MyStores(ExtLessJsonStore(stores_json_path_format))
        from py2store.trans import add_ipython_key_completions

        mystores = add_ipython_key_completions(mystores)
        mystores.dirpath = user_configs_dirpath

    else:
        warn(
            f"The configs directory wasn't found (please make it): {user_configs_dirpath}"
        )
        user_configs_filepath = os.path.expanduser(
            getenv(
                "PY2STORE_CONFIGS_JSON_FILEPATH", "~/.py2store_configs.json"
            )
        )
        if os.path.isfile(user_configs_filepath):
            user_configs_dict = json.load(open(user_configs_filepath))
            user_configs = DictAttr(
                **{str_to_var_str(k): v for k, v in user_configs_dict.items()}
            )

    user_defaults_filepath = os.path.expanduser(
        getenv("PY2STORE_DEFAULTS_JSON_FILEPATH", "~/.py2store_defaults.json")
    )
    if os.path.isfile(user_defaults_filepath):
        user_defaults_dict = json.load(open(user_defaults_filepath))
        user_defaults = DictAttr(
            **{str_to_var_str(k): v for k, v in user_defaults_dict.items()}
        )

except Exception as e:
    warn(
        f"There was an exception when trying to get configs and defaults: {e}"
    )
