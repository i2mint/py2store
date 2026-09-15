"""
Base classes and helpers to read and write local files as key-value collections.

Keys are full file paths. The pieces here (path listing, key validation from a path template,
read, write and delete through ``open``) are what ``py2store.stores.local_store`` assembles
into stores with relative keys.

Main entry points:

- ``FileReader``: a directory as a read-only mapping (subdirectories give nested readers, files give ``bytes``)
- ``DirReader``: the subdirectories of a directory, as a mapping
- ``PathFormatPersister``: read, write and delete the files whose paths match a template
- ``iter_filepaths_in_folder_recursively``: the paths of all files under a folder

>>> import os, tempfile
>>> rootdir = tempfile.mkdtemp()
>>> _ = open(os.path.join(rootdir, 'a.txt'), 'w').write('hi')
>>> [os.path.basename(p) for p in iter_filepaths_in_folder_recursively(rootdir)]
['a.txt']
"""
import os
import re
from glob import iglob
from pathlib import Path
from itertools import takewhile

from dol.errors import NoSuchKeyError
from dol.base import KeyValidationABC, KvReader
from dol.mixins import FilteredKeysMixin, IterBasedSizedMixin

from py2store.parse_format import match_re_for_fstring


# # TODO: These imports are for back compatibility and should be removed at some point
# from py2store.slib.zipfile import ZipReader, ZipFileReader, ZipFilesReader, FilesOfZip
# from py2store.filesys import FileCollection, DirCollection

DFLT_OPEN_MODE = ''

file_sep = os.path.sep
inf = float('infinity')


class FolderNotFoundError(NoSuchKeyError):
    """Raised when writing to a path whose directory does not exist; the message names the first missing directory."""


########################################################################################################################
# File system navigation: Utils


def ensure_slash_suffix(path: str):
    r"""Add a file separation (/ or \) at the end of path str, if not already present."""
    if not path.endswith(file_sep):
        return path + file_sep
    else:
        return path


def pattern_filter(pattern):
    """Make a predicate that is true for strings matching the regex ``pattern`` from their start."""
    pattern = re.compile(pattern)

    def _pattern_filter(s):
        return pattern.match(s) is not None

    return _pattern_filter


def paths_in_dir_with_slash_suffix_for_dirs(rootdir):
    """Yield the full paths directly under ``rootdir``, with a trailing separator on directories."""
    for f in iglob(ensure_slash_suffix(rootdir) + '*'):
        if os.path.isdir(f):
            yield ensure_slash_suffix(f)
        else:
            yield f


def iter_relative_files_and_folder(root_folder):
    """The names of the files and folders directly under ``root_folder``."""
    root_folder = ensure_slash_suffix(root_folder)
    return map(lambda x: x.replace(root_folder, ''), iglob(root_folder + '*'))


def iter_filepaths_in_folder(root_folder):
    """The full paths of the files and folders directly under ``root_folder``."""
    return (
        os.path.join(root_folder, name)
        for name in iter_relative_files_and_folder(root_folder)
    )


def paths_in_dir(rootdir):
    """The full paths of the files and folders directly under ``rootdir``."""
    return iglob(ensure_slash_suffix(rootdir) + '*')


def filepaths_in_dir(rootdir):
    """The full paths of the files (not the folders) directly under ``rootdir``."""
    return filter(os.path.isfile, iglob(ensure_slash_suffix(rootdir) + '*'))


def dirpaths_in_dir(rootdir):
    """The full paths of the folders directly under ``rootdir``."""
    return filter(os.path.isdir, iglob(ensure_slash_suffix(rootdir) + '*'))


def iter_filepaths_in_folder_recursively(
    root_folder, max_levels=None, _current_level=0
):
    """Yield the full paths of the files under ``root_folder``, recursively.

    Args:
        root_folder: The folder to walk.
        max_levels: How many folder levels below ``root_folder`` to descend into: ``0`` yields
            only the files directly under it, ``None`` means no limit.
    """
    if max_levels is None:
        max_levels = inf
    for full_path in paths_in_dir(root_folder):
        if os.path.isdir(full_path):
            if _current_level < max_levels:
                yield from iter_filepaths_in_folder_recursively(
                    full_path, max_levels, _current_level + 1
                )
        else:
            if os.path.isfile(full_path):
                yield full_path


def iter_dirpaths_in_folder_recursively(root_folder, max_levels=None, _current_level=0):
    """Yield the full paths of the folders under ``root_folder``, recursively (``max_levels`` as in ``iter_filepaths_in_folder_recursively``)."""
    if max_levels is None:
        max_levels = inf
    for full_path in paths_in_dir(root_folder):
        if os.path.isdir(full_path):
            yield full_path
            if _current_level < max_levels:
                yield from iter_dirpaths_in_folder_recursively(
                    full_path, max_levels, _current_level + 1
                )


class PrefixedFilepaths:
    """
    Keys collection for local files, where the keys are full filepaths DIRECTLY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    _max_levels = None

    def __iter__(self):
        return iter_relative_files_and_folder(self._prefix, max_levels=self._max_levels)

    def __contains__(self, k):
        """
        Check if filepath exists (i.e. the path exists and is a file)

        :param k: A key to search for
        :return: True if k exists, False if not
        """
        return os.path.isfile(k)


class PrefixedFilepathsRecursive(PrefixedFilepaths):
    """
    Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    _max_levels = None

    def __iter__(self):
        return iter_filepaths_in_folder_recursively(
            self._prefix, max_levels=self._max_levels
        )


class PrefixedDirpathsRecursive(PrefixedFilepaths):
    """
    Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    _max_levels = None

    def __iter__(self):
        return iter_dirpaths_in_folder_recursively(
            self._prefix, max_levels=self._max_levels
        )


def path_match_regex_from_path_format(path_format):
    """Compile the regex that full paths matching the ``path_format`` template satisfy (a bare directory matches everything under it)."""
    if '{' not in path_format:
        # if the path_format is equal to the _prefix (i.e. there's no {} formatting)
        # ... append a formatting element so that the matcher can match all subfiles.
        path_format = path_format + '{}'

    return match_re_for_fstring(path_format)


class PathFormat:
    """Key validation from a path template: which full paths belong to the collection.

    Args:
        path_format: The f-string template that the full path keys should match: a root
            directory (``'/data/'``, everything under it) or a template such as
            ``'/data/{}.csv'`` (only ``.csv`` files under ``/data/``). The directory
            containing the part before the first ``{`` is the root, available as ``_prefix``.

    >>> pf = PathFormat('/data/{}.csv')
    >>> pf._prefix, pf.is_valid_key('/data/a.csv'), pf.is_valid_key('/data/a.txt')
    ('/data/', True, False)
    """

    def __init__(self, path_format: str):
        self._path_format = (
            path_format  # not intended for use, but keeping in case, for now
        )

        if '{' not in path_format:
            rootdir = ensure_slash_suffix(path_format)
        else:
            rootdir = ensure_slash_suffix(
                os.path.dirname(re.match(r'[^{]*', path_format).group(0))
            )

        self._prefix = rootdir
        self._path_match_re = path_match_regex_from_path_format(path_format)

        def _key_filt(k):
            return bool(self._path_match_re.match(k))

        self._key_filt = _key_filt

    def is_valid_key(self, k):
        """Whether ``k`` matches the path template."""
        return self._key_filt(k)


def _is_not_dir(p):
    return not p.is_dir()


def first_non_existing_parent_dir(dirpath):
    """The highest ancestor directory of ``dirpath`` that does not exist, or ``''`` if they all exist."""
    parent = ''
    for parent in takewhile(_is_not_dir, Path(dirpath).parents):
        pass
    return str(parent)


########################################################################################################################
# Local File Persistence : Classes

from functools import wraps
from typing import Union
from collections.abc import Callable


def w_helpful_folder_not_found_error(
    *,
    raise_error=KeyError,
    extra_msg: str | Callable = '',
    caught_errors=FileNotFoundError,
):
    """Decorator factory: re-raise ``caught_errors`` from a method as ``raise_error``, with the original message plus ``extra_msg`` (a string, or a callable of the method's arguments)."""
    if isinstance(extra_msg, str):
        extra_msg_str = extra_msg

        def extra_msg(*args, **kwargs):
            return extra_msg_str

    assert callable(extra_msg), 'extra_msg must be a callable or a string'

    def _helpful_folder_not_found_error(method):
        @wraps(method)
        def wrapped_method(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except caught_errors as e:
                msg = f'{type(e).__name__}: {e}\n' + extra_msg(*args, **kwargs)
                raise raise_error(msg)

        return wrapped_method

    return _helpful_folder_not_found_error


def _store_does_not_create_dirs_msg(self, k, *args, **kwargs):
    return (
        "The store you're using doesn't create directories for you. "
        'You have to make the directories needed yourself manually, '
        'or use a store that does that for you (example QuickStore). '
        "This is the first directory that didn't exist:\n"
        f'{first_non_existing_parent_dir(k)}'
    )


class LocalFileStreamGetter:
    """A class to get stream objects of local open files.
    The class can only get keys, and only to read, write (destructive or append).

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
    """

    def __init__(self, **open_kwargs):
        self.open_kwargs = open_kwargs

    @w_helpful_folder_not_found_error()
    def __getitem__(self, k):
        return open(k, **self.open_kwargs)


# TODO: Use LocalFileStream
class LocalFileRWD:
    """
    A class providing get, set and delete functionality using local files as the storage backend.
    """

    def __init__(self, mode='', **open_kwargs):
        assert mode in {'', 'b', 't'}, "mode should be '', 'b', or 't'"

        read_mode = open_kwargs.pop('read_mode', 'r' + mode)
        write_mode = open_kwargs.pop('write_mode', 'w' + mode)
        self._open_kwargs_for_read = dict(open_kwargs, mode=read_mode)
        self._open_kwargs_for_write = dict(open_kwargs, mode=write_mode)

    @w_helpful_folder_not_found_error()
    def __getitem__(self, k):
        with open(k, **self._open_kwargs_for_read) as fp:
            data = fp.read()
        return data

    @w_helpful_folder_not_found_error(
        raise_error=FolderNotFoundError, extra_msg=_store_does_not_create_dirs_msg,
    )
    def __setitem__(self, k, v):
        with open(k, **self._open_kwargs_for_write) as fp:
            fp.write(v)

    @w_helpful_folder_not_found_error()
    def __delitem__(self, k):
        return os.remove(k)


class FilepathFormatKeys(
    PathFormat,
    FilteredKeysMixin,
    KeyValidationABC,
    PrefixedFilepathsRecursive,
    IterBasedSizedMixin,
):
    """Keys collection of the files matching a path template, recursively under its root (``max_levels`` limits the depth)."""

    def __init__(self, path_format: str, max_levels: int = inf):
        super().__init__(path_format)
        self._max_levels = max_levels


class DirpathFormatKeys(
    PathFormat,
    FilteredKeysMixin,
    KeyValidationABC,
    PrefixedDirpathsRecursive,
    IterBasedSizedMixin,
):
    """Keys collection of the folders matching a path template, recursively under its root (``max_levels`` limits the depth)."""

    def __init__(self, path_format: str, max_levels: int = inf):
        super().__init__(path_format)
        self._max_levels = max_levels


class PathFormatPersister(FilepathFormatKeys, LocalFileRWD):
    """Read, write and delete local files whose full paths match a path template.

    Args:
        path_format: The path template (see ``PathFormat``).
        max_levels: How many folder levels below the root to include when iterating.
        mode: ``''``, ``'t'`` or ``'b'``: whether files are opened in text or binary mode.
        **open_kwargs: Forwarded to ``open``; ``read_mode`` and ``write_mode`` entries override
            the modes derived from ``mode``.
    """

    def __init__(
        self, path_format, max_levels: int = inf, mode=DFLT_OPEN_MODE, **open_kwargs,
    ):
        FilepathFormatKeys.__init__(self, path_format)
        LocalFileRWD.__init__(self, mode, **open_kwargs)
        self._max_levels = max_levels


class PrefixedFilepaths:
    """
    Keys collection for local files, where the keys are full filepaths DIRECTLY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    def __iter__(self):
        return iter_relative_files_and_folder(self._prefix)

    def __contains__(self, k):
        """
        Check if filepath exists (i.e. the path exists and is a file)

        :param k: A key to search for
        :return: True if k exists, False if not
        """
        return os.path.isfile(k)


class PrefixedFilepathsRecursive(PrefixedFilepaths):
    """
    Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    def __iter__(self):
        return iter_filepaths_in_folder_recursively(self._prefix)


class PrefixedDirpathsRecursive(PrefixedFilepaths):
    """
    Keys collection for local files, where the keys are full filepaths RECURSIVELY under a given root dir _prefix.
    This mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)).
    """

    def __iter__(self):
        return iter_dirpaths_in_folder_recursively(self._prefix)


is_dir_path = os.path.isdir
is_file_path = os.path.isfile


def extend_prefix(prefix, new_prefix):
    """Join ``new_prefix`` to ``prefix``, with a trailing separator."""
    return ensure_slash_suffix(os.path.join(prefix, new_prefix))


def endswith_slash(path):
    """Whether ``path`` ends with the OS path separator."""
    return path.endswith(file_sep)


class FileReader(KvReader):
    """KV Reader whose keys are paths and values are:

    - Another FileReader if a path points to a directory
    - The bytes of the file if the path points to a file.

    Keys are the full paths directly under ``rootdir``; directory keys end with a separator.

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
    """

    def __init__(self, rootdir):
        self.rootdir = ensure_slash_suffix(rootdir)
        self._rootdir_length = len(self.rootdir)
        # TODO: Look into alternatives for the raison d'etre of _new_node and _class_name
        # (They are there, because using self.__class__ directly goes to super)
        self._new_node = type(self)
        self._class_name = type(self).__name__

    def _extended_prefix(self, new_prefix):
        return os.path.join(self.rootdir, new_prefix)

    # TODO: Possible optimization: Think if using cached keys makes more sense.
    def __contains__(self, k):
        return (
            k.startswith(self.rootdir)  # prefix is rootdir
            and os.path.exists(k)  # exists (as file or dir)
            and (
                k.endswith(file_sep) or file_sep not in k[self._rootdir_length :]
            )  # is a dir or a first-level file
        )

    def __iter__(self):
        for path in map(
            self._extended_prefix,  # (2) extend prefix with sub-path name
            os.listdir(self.rootdir),  # (1) list file names under _prefix
        ):
            if is_dir_path(path):
                yield ensure_slash_suffix(path)
            else:
                yield path

    def __getitem__(self, k):
        if k in self:
            if is_dir_path(k):
                return self._new_node(k)
            elif is_file_path(k):
                with open(k, 'rb') as fp:
                    return fp.read()
        return self.__missing__(
            k
        )  # if you got this far, the key is missing (or malformed)

    def __missing__(self, k):
        raise NoSuchKeyError(
            f"No such key (perhaps it's not a valid path, or was deleted?): {k}"
        )

    def __repr__(self):
        return f"{self._class_name}('{self.rootdir}')"


class DirReader(FileReader):
    """KV Reader whose keys are the full paths of the subdirectories of ``rootdir`` and whose values are ``DirReader`` instances of them.

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
    """

    def __contains__(self, k):
        return endswith_slash(k) and super().__contains__(k)

    def __iter__(self):
        return filter(endswith_slash, super().__iter__())
