# py2store.serializers.pickled

functions to pickle objects

### Functions

| [`mk_marshal_rw_funcs`](#py2store.serializers.pickled.mk_marshal_rw_funcs)(\*\*kwargs)                  | Generates a reader and writer using marshal.   |
|---------------------------------------------------------------------------------------------------|------------------------------------------------|
| [`mk_pickle_rw_funcs`](#py2store.serializers.pickled.mk_pickle_rw_funcs)([fix_imports, protocol, ...]) | Generates a reader and writer using pickle.    |

### py2store.serializers.pickled.mk_marshal_rw_funcs(\*\*kwargs)

Generates a reader and writer using marshal. That is, a pair of parametrized loads and dumps

```pycon
>>> read, write = mk_marshal_rw_funcs()
>>> d = {'a': 'simple', 'and': {'a': b'more', 'complex': [1, 2.2]}}
>>> serialized_d = write(d)
>>> deserialized_d = read(serialized_d)
>>> assert d == deserialized_d
```

### py2store.serializers.pickled.mk_pickle_rw_funcs(fix_imports=True, protocol=None, pickle_encoding='ASCII', pickle_errors='strict')

Generates a reader and writer using pickle. That is, a pair of parametrized loads and dumps

```pycon
>>> read, write = mk_pickle_rw_funcs()
>>> d = {'a': 'simple', 'and': {'a': b'more', 'complex': [1, 2.2, dict]}}
>>> serialized_d = write(d)
>>> deserialized_d = read(serialized_d)
>>> assert d == deserialized_d
```
