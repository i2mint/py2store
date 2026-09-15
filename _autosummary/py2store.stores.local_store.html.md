# py2store.stores.local_store

Stores that read and write local files as key-value mappings.

Keys are paths relative to a root directory and values are the file contents (text, bytes,
or objects through pickle or json serialization). The `Local*Store` classes need the
directories to exist already; the `Quick*Store` classes create missing directories on write
and pick a temporary root when none is given.

Main entry points:

- `LocalTextStore`, `LocalBinaryStore`: file contents as `str` or `bytes`
- `LocalPickleStore`, `LocalJsonStore`: values serialized with pickle or json
- `QuickStore`: `LocalPickleStore` with a temporary default root and directories created on write
- `DirStore`: the subdirectories of a directory, as nested stores

```pycon
>>> import tempfile
>>> s = LocalTextStore(tempfile.mkdtemp())
>>> s['hello.txt'] = 'world'
>>> list(s), s['hello.txt']
(['hello.txt'], 'world')
```

### Functions

| [`mk_absolute_path`](#py2store.stores.local_store.mk_absolute_path)(path_format)         | Expand a leading `~` and make a path starting with `.` absolute; other paths are returned unchanged.   |
|----------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| [`mk_tmp_quick_store_dirpath`](#py2store.stores.local_store.mk_tmp_quick_store_dirpath)([dirname]) | Path of `dirname` under the system temp directory (`tempfile.gettempdir()`).                           |

### Classes

| [`AutoMkDirsOnSetitemMixin`](#py2store.stores.local_store.AutoMkDirsOnSetitemMixin)()                       | A mixin that will automatically create directories on setitem, when missing.                                              |
|---------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [`AutoMkPathformatMixin`](#py2store.stores.local_store.AutoMkPathformatMixin)([path_format, max_levels]) | A mixin that will choose a path_format if none given                                                                      |
| [`DirStore`](#py2store.stores.local_store.DirStore)(rootdir)                                | A store for local directories.                                                                                            |
| [`LocalBinaryStore`](#py2store.stores.local_store.LocalBinaryStore)(path_format[, max_levels])      | Local files store for binary data: like `LocalTextStore`, but values are `bytes`.                                         |
| [`LocalJsonStore`](#py2store.stores.local_store.LocalJsonStore)(path_format[, max_levels])        | Local files store for JSON data: values are read with `json.loads` and written with `json.dumps`.                         |
| [`LocalPickleStore`](#py2store.stores.local_store.LocalPickleStore)(path_format[, max_levels, ...]) | Local files store with pickle serialization: values are any picklable Python object.                                      |
| [`LocalStore`](#py2store.stores.local_store.LocalStore)                                       |                                                                                                                           |
| [`LocalTextStore`](#py2store.stores.local_store.LocalTextStore)(path_format[, max_levels])        | Local files store for text data: keys are paths relative to the root, values are `str`.                                   |
| [`PathFormatStore`](#py2store.stores.local_store.PathFormatStore)(path_format[, max_levels, mode]) | Local file store using templated relative paths.                                                                          |
| [`PathFormatStoreWithPrefix`](#py2store.stores.local_store.PathFormatStoreWithPrefix)(path_format[, ...])    | `PathFormatStore` wrapped in a `Store`, with the root directory available as `_prefix`.                                   |
| [`PickleStore`](#py2store.stores.local_store.PickleStore)                                      |                                                                                                                           |
| [`QuickBinaryStore`](#py2store.stores.local_store.QuickBinaryStore)([path_format, max_levels])      | `LocalBinaryStore` with a temporary default root and directories created on write.                                        |
| [`QuickJsonStore`](#py2store.stores.local_store.QuickJsonStore)([path_format, max_levels])        | `QuickTextStore` whose values are read with `json.loads` and written with `json.dumps`.                                   |
| [`QuickLocalStoreMixin`](#py2store.stores.local_store.QuickLocalStoreMixin)([path_format, max_levels])  | A mixin that will choose a path_format if none given, and will automatically create directories on setitem, when missing. |
| [`QuickPickleStore`](#py2store.stores.local_store.QuickPickleStore)([path_format, max_levels])      | `LocalPickleStore` with a temporary default root and directories created on write.                                        |
| [`QuickStore`](#py2store.stores.local_store.QuickStore)                                       |                                                                                                                           |
| [`QuickTextStore`](#py2store.stores.local_store.QuickTextStore)([path_format, max_levels])        | `LocalTextStore` with a temporary default root and directories created on write.                                          |
| [`RelativeDirPathFormatKeys`](#py2store.stores.local_store.RelativeDirPathFormatKeys)(path_format[, ...])    | `DirpathFormatKeys` (the folders under a root) wrapped in a `Store` with keys relative to the root.                       |
| [`RelativePathFormatStore2`](#py2store.stores.local_store.RelativePathFormatStore2)(path_format[, ...])     | `PathFormatStoreWithPrefix` with keys made relative to the root directory.                                                |

### *class* py2store.stores.local_store.AutoMkDirsOnSetitemMixin

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A mixin that will automatically create directories on setitem, when missing.

### *class* py2store.stores.local_store.AutoMkPathformatMixin(path_format=None, max_levels=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A mixin that will choose a path_format if none given

#### *classmethod* mk_tmp_quick_store_path_format(subpath='')

Path of `subpath` under the class’s folder (`_tmp_dirname`) in the system temp directory.

### *class* py2store.stores.local_store.DirStore(rootdir)

Bases: `Store`

A store for local directories.
Keys are directory names and values are subdirectory DirStores.

```pycon
>>> from py2store import __file__
>>> import os
>>> root = os.path.dirname(__file__)
>>> s = DirStore(root)
>>> assert set(s).issuperset({'stores', 'persisters', 'serializers', 'key_mappers'})
```

### *class* py2store.stores.local_store.LocalBinaryStore(path_format, max_levels=None)

Bases: [`PathFormatPersister`](py2store.persisters.local_files.html.md#py2store.persisters.local_files.PathFormatPersister)

Local files store for binary data: like `LocalTextStore`, but values are `bytes`.

```pycon
>>> import tempfile
>>> s = LocalBinaryStore(tempfile.mkdtemp())
>>> s['raw.bin'] = b'ab'
>>> s['raw.bin']
b'ab'
```

### *class* py2store.stores.local_store.LocalJsonStore(path_format, max_levels=None)

Bases: `SimpleJsonMixin`, [`LocalTextStore`](#py2store.stores.local_store.LocalTextStore)

Local files store for JSON data: values are read with `json.loads` and written with `json.dumps`.

```pycon
>>> import tempfile
>>> s = LocalJsonStore(tempfile.mkdtemp())
>>> s['conf.json'] = {'a': 1}
>>> s['conf.json']
{'a': 1}
```

### *class* py2store.stores.local_store.LocalPickleStore(path_format, max_levels=None, fix_imports=True, protocol=None, pickle_encoding='ASCII', pickle_errors='strict', \*\*open_kwargs)

Bases: [`PathFormatPersister`](py2store.persisters.local_files.html.md#py2store.persisters.local_files.PathFormatPersister)

Local files store with pickle serialization: values are any picklable Python object.

* **Parameters:**
  * **path_format** – The root directory, optionally with a `{}` template (see `LocalTextStore`).
  * **max_levels** – How many directory levels below the root to include when iterating.
  * **fix_imports** – Forwarded to `pickle.dumps` and `pickle.loads`.
  * **protocol** – The pickle protocol used when writing.
  * **pickle_encoding** – Forwarded to `pickle.loads`.
  * **pickle_errors** – Forwarded to `pickle.loads`.
  * **\*\*open_kwargs** – Forwarded to `open` when reading and writing files.
* **Raises:**
  [**ModuleNotFoundError**](https://docs.python.org/3/builtins/exceptions.html#ModuleNotFoundError) – When unpickling a value needs a module that cannot be imported
      (the message names the key).

```pycon
>>> import tempfile
>>> s = LocalPickleStore(tempfile.mkdtemp())
>>> s['obj'] = {'x': [1, 2]}
>>> s['obj']
{'x': [1, 2]}
>>> s.head()
('obj', {'x': [1, 2]})
```

#### *classmethod* for_dill(path_format, max_levels=None, open_kwargs=None, \*args, \*\*kwargs)

Make a store that serializes with `dill` instead of `pickle`; `*args` and `**kwargs` go to `mk_dill_rw_funcs`.

#### head()

Return the first `(key, value)` item, or `None` if the store is empty.

### py2store.stores.local_store.LocalStore

alias of [`QuickPickleStore`](#py2store.stores.local_store.QuickPickleStore)

### *class* py2store.stores.local_store.LocalTextStore(path_format, max_levels=None)

Bases: [`PathFormatPersister`](py2store.persisters.local_files.html.md#py2store.persisters.local_files.PathFormatPersister)

Local files store for text data: keys are paths relative to the root, values are `str`.

Directories are not created for you: writing under a missing directory raises
`FolderNotFoundError`. Use `QuickTextStore` to have them created on write.

* **Parameters:**
  * **path_format** – The root directory, optionally followed by a `{}` template (for example
    `'/data/{}.txt'`) that restricts which files under the root are listed
    (a key that does not match the template can still be read or written).
  * **max_levels** – How many directory levels below the root to include when iterating
    (`None` for no limit).

```pycon
>>> import os, tempfile
>>> rootdir = tempfile.mkdtemp()
>>> s = LocalTextStore(rootdir)
>>> len(s)
0
>>> s['hello.txt'] = 'world'
>>> list(s), s['hello.txt'], 'hello.txt' in s
(['hello.txt'], 'world', True)
```

A template filters the listing; it does not change how a key is written:

```pycon
>>> only_txt = LocalTextStore(os.path.join(rootdir, '{}.txt'))
>>> only_txt['notes'] = 'x'  # written to rootdir/notes, not rootdir/notes.txt
>>> list(only_txt)
['hello.txt']
```

### *class* py2store.stores.local_store.PathFormatStore(path_format, max_levels=inf, mode='', \*\*open_kwargs)

Bases: [`PathFormatPersister`](py2store.persisters.local_files.html.md#py2store.persisters.local_files.PathFormatPersister), `KvPersister`

Local file store using templated relative paths.

```pycon
>>> from tempfile import gettempdir
>>> import os
>>>
>>> def write_to_key(fullpath_of_relative_path, relative_path, content):  # a function to write content in files
...    with open(fullpath_of_relative_path(relative_path), 'w') as fp:
...        fp.write(content)
>>>
>>> # Preparation: Make a temporary rootdir and write two files in it
>>> rootdir = os.path.join(gettempdir(), 'path_format_store_test' + os.sep)
>>> if not os.path.isdir(rootdir):
...     os.mkdir(rootdir)
>>> # recreate directory (remove existing files, delete directory, and re-create it)
>>> for f in os.listdir(rootdir):
...     fullpath = os.path.join(rootdir, f)
...     if os.path.isfile(fullpath):
...         os.remove(os.path.join(rootdir, f))
>>> if os.path.isdir(rootdir):
...     os.rmdir(rootdir)
>>> if not os.path.isdir(rootdir):
...    os.mkdir(rootdir)
>>>
>>> filepath_of = lambda p: os.path.join(rootdir, p)  # a function to get a fullpath from a relative one
>>> # and make two files in this new dir, with some content
>>> write_to_key(filepath_of, 'a', 'foo')
>>> write_to_key(filepath_of, 'b', 'bar')
>>>
>>> # point the obj source to the rootdir
>>> s = PathFormatStore(path_format=rootdir)
>>>
>>> # assert things...
>>> assert s._prefix == rootdir  # the _rootdir is the one given in constructor
>>> assert s[filepath_of('a')] == 'foo'  # (the filepath for) 'a' contains 'foo'
>>>
>>> # two files under rootdir (as long as the OS didn't create it's own under the hood)
>>> len(s)
2
>>> assert sorted(s) == sorted([filepath_of('a'), filepath_of('b')])  # there's two files in s
>>> filepath_of('a') in s  # rootdir/a is in s
True
>>> filepath_of('not_there') in s  # rootdir/not_there is not in s
False
>>> filepath_of('not_there') not in s  # rootdir/not_there is not in s
True
>>> assert sorted(s.keys()) == sorted([filepath_of('a'), filepath_of('b')])  # the keys (filepaths) of s
>>> sorted(s.values()) # the values of s (contents of files)
['bar', 'foo']
>>> assert sorted(s.items()) == sorted([(filepath_of('a'), 'foo'), (filepath_of('b'), 'bar')])  # the (path, content) items
>>> assert s.get('this key is not there', None) is None  # trying to get the val of a non-existing key returns None
>>> s.get('this key is not there', 'some default value')  # ... or whatever you say
'some default value'
>>>
>>> # add more files to the same folder
>>> write_to_key(filepath_of, 'this.txt', 'this')
>>> write_to_key(filepath_of, 'that.txt', 'blah')
>>> write_to_key(filepath_of, 'the_other.txt', 'bloo')
>>> # see that you now have 5 files
>>> len(s)
5
>>> # and these files contain values:
>>> sorted(s.values())
['bar', 'blah', 'bloo', 'foo', 'this']
>>>
>>> # but if we make an obj source to only take files whose extension is '.txt'...
>>> s = PathFormatStore(path_format=rootdir + '{}.txt')
>>>
>>> rootdir_2 = os.path.join(gettempdir(), 'obj_source_test_2') # get another rootdir
>>> if not os.path.isdir(rootdir_2):
...    os.mkdir(rootdir_2)
>>> filepath_of_2 = lambda p: os.path.join(rootdir_2, p)
>>> # and make two files in this new dir, with some content
>>> write_to_key(filepath_of, 'this.txt', 'this')
>>> write_to_key(filepath_of, 'that.txt', 'blah')
>>> write_to_key(filepath_of, 'the_other.txt', 'bloo')
>>>
>>> ss = PathFormatStore(path_format=rootdir_2 + '{}.txt')
>>>
>>> assert s != ss  # though pointing to identical content, o and oo are not equal since the paths are not equal!
```

### *class* py2store.stores.local_store.PathFormatStoreWithPrefix(path_format, max_levels=inf, mode='', \*\*open_kwargs)

Bases: `Store`

`PathFormatStore` wrapped in a `Store`, with the root directory available as `_prefix`.

### py2store.stores.local_store.PickleStore

alias of [`LocalPickleStore`](#py2store.stores.local_store.LocalPickleStore)

### *class* py2store.stores.local_store.QuickBinaryStore(path_format=None, max_levels=None)

Bases: [`QuickLocalStoreMixin`](#py2store.stores.local_store.QuickLocalStoreMixin), [`LocalBinaryStore`](#py2store.stores.local_store.LocalBinaryStore)

`LocalBinaryStore` with a temporary default root and directories created on write.

### *class* py2store.stores.local_store.QuickJsonStore(path_format=None, max_levels=None)

Bases: `SimpleJsonMixin`, [`QuickTextStore`](#py2store.stores.local_store.QuickTextStore)

`QuickTextStore` whose values are read with `json.loads` and written with `json.dumps`.

### *class* py2store.stores.local_store.QuickLocalStoreMixin(path_format=None, max_levels=None)

Bases: [`AutoMkPathformatMixin`](#py2store.stores.local_store.AutoMkPathformatMixin), [`AutoMkDirsOnSetitemMixin`](#py2store.stores.local_store.AutoMkDirsOnSetitemMixin)

A mixin that will choose a path_format if none given,
and will automatically create directories on setitem, when missing.

### *class* py2store.stores.local_store.QuickPickleStore(path_format=None, max_levels=None)

Bases: [`QuickLocalStoreMixin`](#py2store.stores.local_store.QuickLocalStoreMixin), [`LocalPickleStore`](#py2store.stores.local_store.LocalPickleStore)

`LocalPickleStore` with a temporary default root and directories created on write.

This is what `QuickStore` and `LocalStore` name. Without a `path_format` a folder
under the system temp directory is used, and its path is printed.

```pycon
>>> import os, tempfile
>>> s = QuickPickleStore(os.path.join(tempfile.mkdtemp(), 'quick'))
>>> s['deep/er/key'] = [1, 2]
>>> s['deep/er/key'], list(s)
([1, 2], ['deep/er/key'])
```

### py2store.stores.local_store.QuickStore

alias of [`QuickPickleStore`](#py2store.stores.local_store.QuickPickleStore)

### *class* py2store.stores.local_store.QuickTextStore(path_format=None, max_levels=None)

Bases: [`QuickLocalStoreMixin`](#py2store.stores.local_store.QuickLocalStoreMixin), [`LocalTextStore`](#py2store.stores.local_store.LocalTextStore)

`LocalTextStore` with a temporary default root and directories created on write.

```pycon
>>> import os, tempfile
>>> s = QuickTextStore(os.path.join(tempfile.mkdtemp(), 'sub'))
>>> s['x/y.txt'] = 'z'  # sub/ and sub/x/ are created for you
>>> list(s), s['x/y.txt']
(['x/y.txt'], 'z')
```

### *class* py2store.stores.local_store.RelativeDirPathFormatKeys(path_format, max_levels=inf)

Bases: `PrefixRelativizationMixin`, `Store`

`DirpathFormatKeys` (the folders under a root) wrapped in a `Store` with keys relative to the root.

### *class* py2store.stores.local_store.RelativePathFormatStore2(path_format, max_levels=inf, mode='', \*\*open_kwargs)

Bases: `PrefixRelativizationMixin`, [`PathFormatStoreWithPrefix`](#py2store.stores.local_store.PathFormatStoreWithPrefix)

`PathFormatStoreWithPrefix` with keys made relative to the root directory.

### py2store.stores.local_store.mk_absolute_path(path_format)

Expand a leading `~` and make a path starting with `.` absolute; other paths are returned unchanged.

### py2store.stores.local_store.mk_tmp_quick_store_dirpath(dirname='')

Path of `dirname` under the system temp directory (`tempfile.gettempdir()`).
