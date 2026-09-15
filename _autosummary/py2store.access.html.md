# py2store.access

Utils to load stores from store specifications.
Includes the logic to allow configurations (and defaults) to be parametrized by external environmental
variables and files.

Every data-sourced problem has it’s problem-relevant stores. Once you get your stores right, along with the
right access credentials, indexing, serialization, caching, filtering etc. you’d like to be able to name, save
and/or share this specification, and easily get access to it later on.

Here are tools to help you out.

There are two main key-value stores: One for configurations the user wants to reuse, and the other for the user’s
desired defaults. Both have the same structure:

> * first level key: Name of the resource (should be a valid python variable name)
> * The reminder is more or less free form (until the day we lay out some schemas for this)

The system will look for the specification of user_configs and user_defaults in a json file.
The filepath to this json file can specified in environment variables

> PY2STORE_CONFIGS_JSON_FILEPATH and PY2STORE_DEFAULTS_JSON_FILEPATH

respectively.
By default, they are:

```default
~/.py2store_configs.json and ~/.py2store_defaults.json
```

respectively.

### Functions

| [`add_json_ext`](#py2store.access.add_json_ext)(k)                           | Append `.json` to `k`.                                                                                                                                   |
|--------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`assert_callable`](#py2store.access.assert_callable)(f)                        | Return `f` unchanged if it is callable, else raise `AssertionError`.                                                                                     |
| [`compose`](#py2store.access.compose)(\*functions)                      | Make a function that is the composition of the input functions                                                                                           |
| [`dflt_func_loader`](#py2store.access.dflt_func_loader)(f)                       | Loads and returns the function referenced by f, which could be a callable or a DOTPATH_TO_MODULE.FUNC_NAME dotpath string to one, or a pipeline of these |
| [`directory_json_items`](#py2store.access.directory_json_items)()                    | Yield `(name, contents)` for every `.json` file in the user configs directory, warning about files that fail to decode.                                  |
| [`dotpath_to_func`](#py2store.access.dotpath_to_func)(f)                        | Loads and returns the function referenced by f, which could be a callable or a DOTPATH_TO_MODULE.FUNC_NAME dotpath string to one.                        |
| [`dotpath_to_obj`](#py2store.access.dotpath_to_obj)(dotpath)                   | Loads and returns the object referenced by the string DOTPATH_TO_MODULE.OBJ_NAME                                                                         |
| [`fakit`](#py2store.access.fakit)(fak[, func_loader])                 | Execute a fak with given f, a, k and function loader.                                                                                                    |
| [`fakit_from_dict`](#py2store.access.fakit_from_dict)(d[, func_loader])         | Call the function in `d['f']` (through `func_loader`) with the args `d['a']` and kwargs `d['k']`, both optional.                                         |
| [`fakit_from_tuple`](#py2store.access.fakit_from_tuple)(t[, func_loader])        | Call the function in `t[0]` (through `func_loader`) with the args and kwargs in the rest of `t`.                                                         |
| [`getenv`](#py2store.access.getenv)(name[, default])                   | Like os.getenv, but removes a suffix r character if present (problem with some env var systems)                                                          |
| [`mkdir_if_needed`](#py2store.access.mkdir_if_needed)(dirpath[, name, verbose]) | Create `dirpath` if it does not exist, printing a note that calls it `name` (`verbose` is accepted but not used).                                        |
| [`without_json_ext`](#py2store.access.without_json_ext)(_id)                     | Strip the `.json` extension from `_id`.                                                                                                                  |

### Classes

| [`MyConfigs`](#py2store.access.MyConfigs)([max_levels])   |                                                                                                        |
|----------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| [`MyStores`](#py2store.access.MyStores)([store])         | Store specifications (json files under the user configs directory) that instantiate the store on read. |

### *class* py2store.access.MyConfigs(max_levels=None)

Bases: `OverWritesNotAllowedMixin`, [`MyConfigs`](#py2store.access.MyConfigs)

### *class* py2store.access.MyStores(store=<class 'dict'>)

Bases: `Store`

Store specifications (json files under the user configs directory) that instantiate the store on read.

A specification is a dict with a `'$fak'` entry holding an `(f, a, k)` specification, run through `fakit`.

#### *property* configs

The underlying store of raw specifications.

#### *static* func_loader()

Loads and returns the function referenced by f,
which could be a callable or a DOTPATH_TO_MODULE.FUNC_NAME dotpath string to one, or a pipeline of these

* **Return type:**
  `callable`

### py2store.access.add_json_ext(k)

Append `.json` to `k`.

### py2store.access.assert_callable(f)

Return `f` unchanged if it is callable, else raise `AssertionError`.

* **Return type:**
  `callable`

### py2store.access.compose(\*functions)

Make a function that is the composition of the input functions

### py2store.access.dflt_func_loader(f)

Loads and returns the function referenced by f,
which could be a callable or a DOTPATH_TO_MODULE.FUNC_NAME dotpath string to one, or a pipeline of these

* **Return type:**
  `callable`

### py2store.access.directory_json_items()

Yield `(name, contents)` for every `.json` file in the user configs directory, warning about files that fail to decode.

### py2store.access.dotpath_to_func(f)

Loads and returns the function referenced by f,
which could be a callable or a DOTPATH_TO_MODULE.FUNC_NAME dotpath string to one.

* **Return type:**
  `callable`

### py2store.access.dotpath_to_obj(dotpath)

Loads and returns the object referenced by the string DOTPATH_TO_MODULE.OBJ_NAME

### py2store.access.fakit(fak, func_loader=<function dflt_func_loader>)

Execute a fak with given f, a, k and function loader.

Essentially returns `func_loader(f)(*a, **k)`

* **Parameters:**
  * **fak** – A (f, a, k) specification. Could be a tuple or a dict (with ‘f’, ‘a’, ‘k’ keys). All but f are optional.
  * **func_loader** – A function returning a function. This is where you specify any validation of func specification f,
    and/or how to get a callable from it.
* **Returns:**
  A python object.

### py2store.access.fakit_from_dict(d, func_loader=<function assert_callable>)

Call the function in `d['f']` (through `func_loader`) with the args `d['a']` and kwargs `d['k']`, both optional.

### py2store.access.fakit_from_tuple(t, func_loader=<function dflt_func_loader>)

Call the function in `t[0]` (through `func_loader`) with the args and kwargs in the rest of `t`.

`t` has 1 to 3 elements: `(f,)`, `(f, args)`, `(f, kwargs)` or `(f, args, kwargs)`,
where `args` is a tuple or list and `kwargs` a dict.

```pycon
>>> fakit_from_tuple((len, ['abc']))
3
>>> fakit_from_tuple(('builtins.len', ['ab']))
2
>>> fakit_from_tuple((dict, (), {'x': 1}))
{'x': 1}
```

### py2store.access.getenv(name, default=None)

Like os.getenv, but removes a suffix r character if present (problem with some env var systems)

### py2store.access.mkdir_if_needed(dirpath, name=None, verbose=True)

Create `dirpath` if it does not exist, printing a note that calls it `name` (`verbose` is accepted but not used).

### py2store.access.without_json_ext(\_id)

Strip the `.json` extension from `_id`.
