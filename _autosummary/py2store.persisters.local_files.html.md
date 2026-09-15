# py2store.persisters.local_files

Base classes and helpers to read and write local files as key-value collections.

Keys are full file paths. The pieces here (path listing, key validation from a path template,
read, write and delete through `open`) are what `py2store.stores.local_store` assembles
into stores with relative keys.

Main entry points:

- `FileReader`: a directory as a read-only mapping (subdirectories give nested readers, files give `bytes`)
- `DirReader`: the subdirectories of a directory, as a mapping
- `PathFormatPersister`: read, write and delete the files whose paths match a template
- `iter_filepaths_in_folder_recursively`: the paths of all files under a folder

```pycon
>>> import os, tempfile
>>> rootdir = tempfile.mkdtemp()
>>> _ = open(os.path.join(rootdir, 'a.txt'), 'w').write('hi')
>>> [os.path.basename(p) for p in iter_filepaths_in_folder_recursively(rootdir)]
['a.txt']
```

### Functions

| [`dirpaths_in_dir`](#py2store.persisters.local_files.dirpaths_in_dir)(rootdir)                          | The full paths of the folders directly under `rootdir`.                                                                                                                     |
|----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`endswith_slash`](#py2store.persisters.local_files.endswith_slash)(path)                              | Whether `path` ends with the OS path separator.                                                                                                                             |
| [`ensure_slash_suffix`](#py2store.persisters.local_files.ensure_slash_suffix)(path)                         | Add a file separation (/ or ) at the end of path str, if not already present.                                                                                               |
| [`extend_prefix`](#py2store.persisters.local_files.extend_prefix)(prefix, new_prefix)                 | Join `new_prefix` to `prefix`, with a trailing separator.                                                                                                                   |
| [`filepaths_in_dir`](#py2store.persisters.local_files.filepaths_in_dir)(rootdir)                         | The full paths of the files (not the folders) directly under `rootdir`.                                                                                                     |
| [`first_non_existing_parent_dir`](#py2store.persisters.local_files.first_non_existing_parent_dir)(dirpath)            | The highest ancestor directory of `dirpath` that does not exist, or `''` if they all exist.                                                                                 |
| [`iter_dirpaths_in_folder_recursively`](#py2store.persisters.local_files.iter_dirpaths_in_folder_recursively)(root_folder)  | Yield the full paths of the folders under `root_folder`, recursively (`max_levels` as in `iter_filepaths_in_folder_recursively`).                                           |
| [`iter_filepaths_in_folder`](#py2store.persisters.local_files.iter_filepaths_in_folder)(root_folder)             | The full paths of the files and folders directly under `root_folder`.                                                                                                       |
| [`iter_filepaths_in_folder_recursively`](#py2store.persisters.local_files.iter_filepaths_in_folder_recursively)(root_folder) | Yield the full paths of the files under `root_folder`, recursively.                                                                                                         |
| [`iter_relative_files_and_folder`](#py2store.persisters.local_files.iter_relative_files_and_folder)(root_folder)       | The names of the files and folders directly under `root_folder`.                                                                                                            |
| [`path_match_regex_from_path_format`](#py2store.persisters.local_files.path_match_regex_from_path_format)(path_format)    | Compile the regex that full paths matching the `path_format` template satisfy (a bare directory matches everything under it).                                               |
| [`paths_in_dir`](#py2store.persisters.local_files.paths_in_dir)(rootdir)                             | The full paths of the files and folders directly under `rootdir`.                                                                                                           |
| [`paths_in_dir_with_slash_suffix_for_dirs`](#py2store.persisters.local_files.paths_in_dir_with_slash_suffix_for_dirs)(rootdir)  | Yield the full paths directly under `rootdir`, with a trailing separator on directories.                                                                                    |
| [`pattern_filter`](#py2store.persisters.local_files.pattern_filter)(pattern)                           | Make a predicate that is true for strings matching the regex `pattern` from their start.                                                                                    |
| [`w_helpful_folder_not_found_error`](#py2store.persisters.local_files.w_helpful_folder_not_found_error)(\*[, ...])       | Decorator factory: re-raise `caught_errors` from a method as `raise_error`, with the original message plus `extra_msg` (a string, or a callable of the method's arguments). |

### Classes

| [`DirReader`](#py2store.persisters.local_files.DirReader)(rootdir)                            | KV Reader whose keys are the full paths of the subdirectories of `rootdir` and whose values are `DirReader` instances of them.   |
|------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| [`DirpathFormatKeys`](#py2store.persisters.local_files.DirpathFormatKeys)(path_format[, max_levels])  | Keys collection of the folders matching a path template, recursively under its root (`max_levels` limits the depth).             |
| [`FileReader`](#py2store.persisters.local_files.FileReader)(rootdir)                           | KV Reader whose keys are paths and values are:                                                                                   |
| [`FilepathFormatKeys`](#py2store.persisters.local_files.FilepathFormatKeys)(path_format[, max_levels]) | Keys collection of the files matching a path template, recursively under its root (`max_levels` limits the depth).               |
| [`LocalFileRWD`](#py2store.persisters.local_files.LocalFileRWD)([mode])                          | A class providing get, set and delete functionality using local files as the storage backend.                                    |
| [`LocalFileStreamGetter`](#py2store.persisters.local_files.LocalFileStreamGetter)(\*\*open_kwargs)        | A class to get stream objects of local open files.                                                                               |
| [`PathFormat`](#py2store.persisters.local_files.PathFormat)(path_format)                       | Key validation from a path template: which full paths belong to the collection.                                                  |
| [`PathFormatPersister`](#py2store.persisters.local_files.PathFormatPersister)(path_format[, ...])       | Read, write and delete local files whose full paths match a path template.                                                       |
| [`PrefixedDirpathsRecursive`](#py2store.persisters.local_files.PrefixedDirpathsRecursive)()                   | Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir \_prefix.                  |
| [`PrefixedFilepaths`](#py2store.persisters.local_files.PrefixedFilepaths)()                           | Keys collection for local files, where the keys are full filepaths DIRECTLY under a given root dir \_prefix.                     |
| [`PrefixedFilepathsRecursive`](#py2store.persisters.local_files.PrefixedFilepathsRecursive)()                  | Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir \_prefix.                  |

### Exceptions

| [`FolderNotFoundError`](#py2store.persisters.local_files.FolderNotFoundError)   | Raised when writing to a path whose directory does not exist; the message names the first missing directory.   |
|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|

### *class* py2store.persisters.local_files.DirReader(rootdir)

Bases: [`FileReader`](#py2store.persisters.local_files.FileReader)

KV Reader whose keys are the full paths of the subdirectories of `rootdir` and whose values are `DirReader` instances of them.

```pycon
>>> import os, tempfile
>>> rootdir = tempfile.mkdtemp()
>>> _ = open(os.path.join(rootdir, 'a.txt'), 'wb').write(b'hi')
>>> os.mkdir(os.path.join(rootdir, 'sub'))
>>> s = DirReader(rootdir)
>>> [k[len(s.rootdir):] for k in s]
['sub/']
>>> os.path.join(rootdir, 'a.txt') in s
False
>>> type(s[os.path.join(rootdir, 'sub', '')]).__name__
'DirReader'
```

### *class* py2store.persisters.local_files.DirpathFormatKeys(path_format, max_levels=inf)

Bases: [`PathFormat`](#py2store.persisters.local_files.PathFormat), `FilteredKeysMixin`, `KeyValidationABC`, [`PrefixedDirpathsRecursive`](#py2store.persisters.local_files.PrefixedDirpathsRecursive), `IterBasedSizedMixin`

Keys collection of the folders matching a path template, recursively under its root (`max_levels` limits the depth).

### *class* py2store.persisters.local_files.FileReader(rootdir)

Bases: `KvReader`

KV Reader whose keys are paths and values are:

- Another FileReader if a path points to a directory
- The bytes of the file if the path points to a file.

Keys are the full paths directly under `rootdir`; directory keys end with a separator.

```pycon
>>> import os, tempfile
>>> rootdir = tempfile.mkdtemp()
>>> _ = open(os.path.join(rootdir, 'a.txt'), 'wb').write(b'hi')
>>> os.mkdir(os.path.join(rootdir, 'sub'))
>>> s = FileReader(rootdir)
>>> sorted(k[len(s.rootdir):] for k in s)
['a.txt', 'sub/']
>>> s[os.path.join(rootdir, 'a.txt')]
b'hi'
>>> type(s[os.path.join(rootdir, 'sub', '')]).__name__
'FileReader'
```

### *class* py2store.persisters.local_files.FilepathFormatKeys(path_format, max_levels=inf)

Bases: [`PathFormat`](#py2store.persisters.local_files.PathFormat), `FilteredKeysMixin`, `KeyValidationABC`, [`PrefixedFilepathsRecursive`](#py2store.persisters.local_files.PrefixedFilepathsRecursive), `IterBasedSizedMixin`

Keys collection of the files matching a path template, recursively under its root (`max_levels` limits the depth).

### *exception* py2store.persisters.local_files.FolderNotFoundError

Bases: `NoSuchKeyError`

Raised when writing to a path whose directory does not exist; the message names the first missing directory.

### *class* py2store.persisters.local_files.LocalFileRWD(mode='', \*\*open_kwargs)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A class providing get, set and delete functionality using local files as the storage backend.

### *class* py2store.persisters.local_files.LocalFileStreamGetter(\*\*open_kwargs)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A class to get stream objects of local open files.
The class can only get keys, and only to read, write (destructive or append).

```pycon
>>> from tempfile import mkdtemp
>>> import os
>>> rootdir = mkdtemp()
>>>
>>> appendable_stream = LocalFileStreamGetter(mode='a+')
>>> reader = PathFormatPersister(rootdir)
>>> filepath = os.path.join(rootdir, 'tmp.txt')
>>>
>>> with appendable_stream[filepath] as fp:
...     fp.write('hello')
5
>>> print(reader[filepath])
hello
>>> with appendable_stream[filepath] as fp:
...     fp.write(' world')
6
>>>
>>> print(reader[filepath])
hello world
```

### *class* py2store.persisters.local_files.PathFormat(path_format)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Key validation from a path template: which full paths belong to the collection.

* **Parameters:**
  **path_format** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The f-string template that the full path keys should match: a root
  directory (`'/data/'`, everything under it) or a template such as
  `'/data/{}.csv'` (only `.csv` files under `/data/`). The directory
  containing the part before the first `{` is the root, available as `_prefix`.

```pycon
>>> pf = PathFormat('/data/{}.csv')
>>> pf._prefix, pf.is_valid_key('/data/a.csv'), pf.is_valid_key('/data/a.txt')
('/data/', True, False)
```

#### is_valid_key(k)

Whether `k` matches the path template.

### *class* py2store.persisters.local_files.PathFormatPersister(path_format, max_levels=inf, mode='', \*\*open_kwargs)

Bases: [`FilepathFormatKeys`](#py2store.persisters.local_files.FilepathFormatKeys), [`LocalFileRWD`](#py2store.persisters.local_files.LocalFileRWD)

Read, write and delete local files whose full paths match a path template.

* **Parameters:**
  * **path_format** – The path template (see `PathFormat`).
  * **max_levels** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – How many folder levels below the root to include when iterating.
  * **mode** – `''`, `'t'` or `'b'`: whether files are opened in text or binary mode.
  * **\*\*open_kwargs** – Forwarded to `open`; `read_mode` and `write_mode` entries override
    the modes derived from `mode`.

### *class* py2store.persisters.local_files.PrefixedDirpathsRecursive

Bases: [`PrefixedFilepaths`](#py2store.persisters.local_files.PrefixedFilepaths)

Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir \_prefix.
This mixin adds iteration (_\_iter_\_), length (_\_len_\_), and containment (_\_contains_\_(k)).

### *class* py2store.persisters.local_files.PrefixedFilepaths

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Keys collection for local files, where the keys are full filepaths DIRECTLY under a given root dir \_prefix.
This mixin adds iteration (_\_iter_\_), length (_\_len_\_), and containment (_\_contains_\_(k)).

### *class* py2store.persisters.local_files.PrefixedFilepathsRecursive

Bases: [`PrefixedFilepaths`](#py2store.persisters.local_files.PrefixedFilepaths)

Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir \_prefix.
This mixin adds iteration (_\_iter_\_), length (_\_len_\_), and containment (_\_contains_\_(k)).

### py2store.persisters.local_files.dirpaths_in_dir(rootdir)

The full paths of the folders directly under `rootdir`.

### py2store.persisters.local_files.endswith_slash(path)

Whether `path` ends with the OS path separator.

### py2store.persisters.local_files.ensure_slash_suffix(path)

Add a file separation (/ or ) at the end of path str, if not already present.

### py2store.persisters.local_files.extend_prefix(prefix, new_prefix)

Join `new_prefix` to `prefix`, with a trailing separator.

### py2store.persisters.local_files.filepaths_in_dir(rootdir)

The full paths of the files (not the folders) directly under `rootdir`.

### py2store.persisters.local_files.first_non_existing_parent_dir(dirpath)

The highest ancestor directory of `dirpath` that does not exist, or `''` if they all exist.

### py2store.persisters.local_files.iter_dirpaths_in_folder_recursively(root_folder, max_levels=None, \_current_level=0)

Yield the full paths of the folders under `root_folder`, recursively (`max_levels` as in `iter_filepaths_in_folder_recursively`).

### py2store.persisters.local_files.iter_filepaths_in_folder(root_folder)

The full paths of the files and folders directly under `root_folder`.

### py2store.persisters.local_files.iter_filepaths_in_folder_recursively(root_folder, max_levels=None, \_current_level=0)

Yield the full paths of the files under `root_folder`, recursively.

* **Parameters:**
  * **root_folder** – The folder to walk.
  * **max_levels** – How many folder levels below `root_folder` to descend into: `0` yields
    only the files directly under it, `None` means no limit.

### py2store.persisters.local_files.iter_relative_files_and_folder(root_folder)

The names of the files and folders directly under `root_folder`.

### py2store.persisters.local_files.path_match_regex_from_path_format(path_format)

Compile the regex that full paths matching the `path_format` template satisfy (a bare directory matches everything under it).

### py2store.persisters.local_files.paths_in_dir(rootdir)

The full paths of the files and folders directly under `rootdir`.

### py2store.persisters.local_files.paths_in_dir_with_slash_suffix_for_dirs(rootdir)

Yield the full paths directly under `rootdir`, with a trailing separator on directories.

### py2store.persisters.local_files.pattern_filter(pattern)

Make a predicate that is true for strings matching the regex `pattern` from their start.

### py2store.persisters.local_files.w_helpful_folder_not_found_error(\*, raise_error=<class 'KeyError'>, extra_msg='', caught_errors=<class 'FileNotFoundError'>)

Decorator factory: re-raise `caught_errors` from a method as `raise_error`, with the original message plus `extra_msg` (a string, or a callable of the method’s arguments).
