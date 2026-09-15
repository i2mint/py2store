# py2store

py2store: tools to create simple and consistent interfaces to complicated and varied data sources.

The core has moved to the `dol` package (Data Object Layer); py2store keeps the original
names, re-exports them, and keeps the local-file stores that still live here. A store is a
`MutableMapping` whose keys and values are transformed on the way in and out, so that files,
zip archives or databases are read and written like a `dict`.

Main entry points:

- `LocalTextStore`, `LocalBinaryStore`, `LocalPickleStore`, `LocalJsonStore`: the files under a root directory as a dict
- `QuickStore`: the pickle store with a temporary default root and directories created on write
- `wrap_kvs`, `filt_iter`, `cached_keys`: transform a store’s keys, values or iteration (from `dol.trans`)
- `kvhead`, `ihead`: peek at the first items of a store or an iterable

```pycon
>>> from py2store import kvhead
>>> kvhead({'a': 1, 'b': 2})
('a', 1)
```

### Functions

| [`ihead`](#py2store.ihead)(store[, n])   | Get the first item of an iterable, or a list of the first `n` items.            |
|----------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`kvhead`](#py2store.kvhead)(store[, n])  | Get the first `(key, value)` item of a store, or a list of the first `n` items. |

### py2store.ihead(store, n=1)

Get the first item of an iterable, or a list of the first `n` items.

With `n=1` the item itself is returned (`None` if the iterable is empty); otherwise a
list of at most `n` items.

```pycon
>>> ihead(iter('abc'))
'a'
>>> ihead('abc', 2)
['a', 'b']
>>> ihead(iter('')) is None
True
```

### py2store.kvhead(store, n=1)

Get the first `(key, value)` item of a store, or a list of the first `n` items.

With `n=1` the item itself is returned (`None` if the store is empty); otherwise a
list of at most `n` items, in the store’s iteration order.

```pycon
>>> kvhead({'a': 1, 'b': 2})
('a', 1)
>>> kvhead({'a': 1, 'b': 2}, 5)
[('a', 1), ('b', 2)]
>>> kvhead({}) is None
True
```

### Modules

| [`access`](py2store.access.html.md#module-py2store.access)                                 | Utils to load stores from store specifications.                                              |
|----------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| [`appendable`](py2store.appendable.html.md#py2store.appendable)([store_cls, return_keys, ...]) | Makes a new class with append (and consequential extend) methods                             |
| [`base`](py2store.base.html.md#module-py2store.base)                                     | Forwards to dol.base:                                                                        |
| [`caching`](py2store.caching.html.md#module-py2store.caching)                               | Forwards to dol.caching:                                                                     |
| [`dig`](py2store.dig.html.md#module-py2store.dig)                                       | Forwards to dol.dig:                                                                         |
| [`errors`](py2store.errors.html.md#module-py2store.errors)                                 | Forwards to dol.errors:                                                                      |
| [`ext`](py2store.ext.html.md#module-py2store.ext)                                       | py2store Extensions, Add-ons, etc.                                                           |
| [`filesys`](py2store.filesys.html.md#module-py2store.filesys)                               | Forwards to dol.filesys:                                                                     |
| [`key_mappers`](py2store.key_mappers.html.md#module-py2store.key_mappers)                       | key mapping                                                                                  |
| [`misc`](py2store.misc.html.md#module-py2store.misc)                                     | Functions to read from and write to misc sources.                                            |
| [`mixins`](py2store.mixins.html.md#module-py2store.mixins)                                 | Forwards to dol.mixins:                                                                      |
| [`my`](py2store.my.html.md#module-py2store.my)                                         | functionalities meant to be configurable                                                     |
| [`naming`](py2store.naming.html.md#module-py2store.naming)                                 | Forwards to dol.naming:                                                                      |
| [`parse_format`](py2store.parse_format.html.md#module-py2store.parse_format)                     | Modified from [https://github.com/r1chardj0n3s/parse](https://github.com/r1chardj0n3s/parse) |
| [`paths`](py2store.paths.html.md#module-py2store.paths)                                   | Forwards to dol.paths:                                                                       |
| [`persisters`](py2store.persisters.html.md#module-py2store.persisters)                         | base persisters -- now all forwarding to separate libraries                                  |
| [`serializers`](py2store.serializers.html.md#module-py2store.serializers)                       | a package of serializers                                                                     |
| [`signatures`](py2store.signatures.html.md#module-py2store.signatures)                         | Forwards to dol.signatures:                                                                  |
| [`slib`](py2store.slib.html.md#module-py2store.slib)                                     | Data Object Layers for a few standard libs.                                                  |
| [`sources`](py2store.sources.html.md#module-py2store.sources)                               | Forwards to dol.sources:                                                                     |
| [`stores`](py2store.stores.html.md#module-py2store.stores)                                 | a package of various stores                                                                  |
| [`test`](py2store.test.html.md#module-py2store.test)                                     | test files                                                                                   |
| [`trans`](py2store.trans.html.md#module-py2store.trans)                                   | Forwards to dol.trans:                                                                       |
| [`util`](py2store.util.html.md#module-py2store.util)                                     | Forwards to dol.util:                                                                        |
| [`utils`](py2store.utils.html.md#module-py2store.utils)                                   | general utils                                                                                |
