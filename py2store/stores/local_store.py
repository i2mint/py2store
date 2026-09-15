"""
Stores that read and write local files as key-value mappings.

Keys are paths relative to a root directory and values are the file contents (text, bytes,
or objects through pickle or json serialization). The ``Local*Store`` classes need the
directories to exist already; the ``Quick*Store`` classes create missing directories on write
and pick a temporary root when none is given.

Main entry points:

- ``LocalTextStore``, ``LocalBinaryStore``: file contents as ``str`` or ``bytes``
- ``LocalPickleStore``, ``LocalJsonStore``: values serialized with pickle or json
- ``QuickStore``: ``LocalPickleStore`` with a temporary default root and directories created on write
- ``DirStore``: the subdirectories of a directory, as nested stores

>>> import tempfile
>>> s = LocalTextStore(tempfile.mkdtemp())
>>> s['hello.txt'] = 'world'
>>> list(s), s['hello.txt']
(['hello.txt'], 'world')
"""
import os
from functools import wraps

from dol.base import Store, Persister
from dol.paths import (
    mk_relative_path_store,
    PrefixRelativization,
    PrefixRelativizationMixin,
)
from dol.mixins import SimpleJsonMixin
from dol.filesys import MakeMissingDirsStoreMixin

MakeMissingDirsStoreMixin  # just to tell linter to not complain (here for backcompat)

from py2store.persisters.local_files import (
    PathFormatPersister,
    DirpathFormatKeys,
    DirReader,
    ensure_slash_suffix,
)
from py2store.serializers.pickled import mk_pickle_rw_funcs


class PathFormatStore(PathFormatPersister, Persister):
    """
    Local file store using templated relative paths.

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
    """

    pass


RelPathLocalFileStore = mk_relative_path_store(
    PathFormatPersister, __name__='RelPathLocalFileStore'
)
RelPathLocalFileStore.__doc__ = '''Local file store using templated relative paths.'''

RelPathLocalFileStoreEnforcingFormat = mk_relative_path_store(
    PathFormatPersister, __name__='RelPathLocalFileStoreEnforcingFormat'
)
RelPathLocalFileStoreEnforcingFormat.__doc__ = '''A RelativePathFormatStore, but that won't allow one to use a key that is not valid 
    (according to the self.store.is_valid_key boolean method)'''

# aliases for back compatibility
RelativePathFormatStore = RelPathLocalFileStore
RelativePathFormatStoreEnforcingFormat = RelPathLocalFileStoreEnforcingFormat


# Old version it replaces
# class RelativePathFormatStore(PrefixRelativizationMixin, Store):
#     """Local file store using templated relative paths.
#     """
#
#     @wraps(PathFormatStore.__init__)
#     def __init__(self, *args, **kwargs):
#         super().__init__(store=PathFormatStore(*args, **kwargs))
#         self._prefix = self.store._prefix
#
#
# class RelativePathFormatStoreEnforcingFormat(RelativePathFormatStore):
#     """A RelativePathFormatStore, but that won't allow one to use a key that is not valid
#     (according to the self.store.is_valid_key boolean method).
#     """
#
#     def _id_of_key(self, k):
#         _id = super()._id_of_key(k)
#         if self.store.is_valid_key(_id):
#             return _id
#         else:
#             raise KeyError(f"Key not valid: {k}")


class PathFormatStoreWithPrefix(Store):
    """``PathFormatStore`` wrapped in a ``Store``, with the root directory available as ``_prefix``."""

    @wraps(PathFormatStore.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(store=PathFormatStore(*args, **kwargs))
        self._prefix = self.store._prefix


# Would like to replace the above pattern with what's below, but
# from py2store.trans import store_wrap
# PathFormatStoreWithPrefix = store_wrap(PathFormatStore, 'PathFormatStoreWithPrefix')


class RelativePathFormatStore2(PrefixRelativizationMixin, PathFormatStoreWithPrefix):
    """``PathFormatStoreWithPrefix`` with keys made relative to the root directory."""


class LocalTextStore(RelativePathFormatStore):
    """Local files store for text data: keys are paths relative to the root, values are ``str``.

    Directories are not created for you: writing under a missing directory raises
    ``FolderNotFoundError``. Use ``QuickTextStore`` to have them created on write.

    Args:
        path_format: The root directory, optionally followed by a ``{}`` template (for example
            ``'/data/{}.txt'``) that restricts which files under the root are listed
            (a key that does not match the template can still be read or written).
        max_levels: How many directory levels below the root to include when iterating
            (``None`` for no limit).

    >>> import os, tempfile
    >>> rootdir = tempfile.mkdtemp()
    >>> s = LocalTextStore(rootdir)
    >>> len(s)
    0
    >>> s['hello.txt'] = 'world'
    >>> list(s), s['hello.txt'], 'hello.txt' in s
    (['hello.txt'], 'world', True)

    A template filters the listing; it does not change how a key is written:

    >>> only_txt = LocalTextStore(os.path.join(rootdir, '{}.txt'))
    >>> only_txt['notes'] = 'x'  # written to rootdir/notes, not rootdir/notes.txt
    >>> list(only_txt)
    ['hello.txt']
    """

    def __init__(self, path_format, max_levels=None):
        super().__init__(path_format, max_levels=max_levels, mode='t')


class LocalBinaryStore(RelativePathFormatStore):
    """Local files store for binary data: like ``LocalTextStore``, but values are ``bytes``.

    >>> import tempfile
    >>> s = LocalBinaryStore(tempfile.mkdtemp())
    >>> s['raw.bin'] = b'ab'
    >>> s['raw.bin']
    b'ab'
    """

    def __init__(self, path_format, max_levels=None):
        super().__init__(path_format, max_levels=max_levels, mode='b')


class LocalPickleStore(RelativePathFormatStore):
    """Local files store with pickle serialization: values are any picklable Python object.

    Args:
        path_format: The root directory, optionally with a ``{}`` template (see ``LocalTextStore``).
        max_levels: How many directory levels below the root to include when iterating.
        fix_imports: Forwarded to ``pickle.dumps`` and ``pickle.loads``.
        protocol: The pickle protocol used when writing.
        pickle_encoding: Forwarded to ``pickle.loads``.
        pickle_errors: Forwarded to ``pickle.loads``.
        **open_kwargs: Forwarded to ``open`` when reading and writing files.

    Raises:
        ModuleNotFoundError: When unpickling a value needs a module that cannot be imported
            (the message names the key).

    >>> import tempfile
    >>> s = LocalPickleStore(tempfile.mkdtemp())
    >>> s['obj'] = {'x': [1, 2]}
    >>> s['obj']
    {'x': [1, 2]}
    >>> s.head()
    ('obj', {'x': [1, 2]})
    """

    def __init__(
        self,
        path_format,
        max_levels=None,
        fix_imports=True,
        protocol=None,
        pickle_encoding='ASCII',
        pickle_errors='strict',
        **open_kwargs,
    ):
        super().__init__(path_format, max_levels=max_levels, mode='b', **open_kwargs)
        self._loads, self._dumps = mk_pickle_rw_funcs(
            fix_imports, protocol, pickle_encoding, pickle_errors
        )

    @classmethod
    def for_dill(cls, path_format, max_levels=None, open_kwargs=None, *args, **kwargs):
        """Make a store that serializes with ``dill`` instead of ``pickle``; ``*args`` and ``**kwargs`` go to ``mk_dill_rw_funcs``."""
        from py2store.serializers.pickled import mk_dill_rw_funcs

        open_kwargs = open_kwargs or {}
        self = cls(path_format, max_levels=max_levels, **open_kwargs)
        self._loads, self._dumps = mk_dill_rw_funcs(*args, **kwargs)
        return self

    def __getitem__(self, k):
        try:
            return self._loads(super().__getitem__(k))
        except (ModuleNotFoundError, AttributeError) as e:
            if isinstance(e, AttributeError) and 'module' not in str(e):
                raise
            else:
                raise type(e)(f'Some modules are missing to unpickle {k}: {e}')

    def __setitem__(self, k, v):
        return super().__setitem__(k, self._dumps(v))

    # TODO: hack to take care of problem with head not playing well with wrappers. Find better solution.
    def head(self):
        """Return the first ``(key, value)`` item, or ``None`` if the store is empty."""
        for k, v in self.items():
            return k, v


class LocalJsonStore(SimpleJsonMixin, LocalTextStore):
    """Local files store for JSON data: values are read with ``json.loads`` and written with ``json.dumps``.

    >>> import tempfile
    >>> s = LocalJsonStore(tempfile.mkdtemp())
    >>> s['conf.json'] = {'a': 1}
    >>> s['conf.json']
    {'a': 1}
    """


PickleStore = LocalPickleStore  # alias


def mk_tmp_quick_store_dirpath(dirname=''):
    """Path of ``dirname`` under the system temp directory (``tempfile.gettempdir()``)."""
    from tempfile import gettempdir

    temp_root = gettempdir()
    return os.path.join(temp_root, dirname)


def mk_absolute_path(path_format):
    """Expand a leading ``~`` and make a path starting with ``.`` absolute; other paths are returned unchanged."""
    if path_format.startswith('~'):
        path_format = os.path.expanduser(path_format)
    elif path_format.startswith('.'):
        path_format = os.path.abspath(path_format)
    return path_format


class AutoMkDirsOnSetitemMixin:
    """A mixin that will automatically create directories on setitem, when missing."""

    def __setitem__(self, k, v):
        dirname = os.path.dirname(os.path.join(self._prefix, k))
        os.makedirs(dirname, exist_ok=True)
        return super().__setitem__(k, v)


class AutoMkPathformatMixin:
    """A mixin that will choose a path_format if none given"""

    _tmp_dirname = 'quick_store'
    _docsuffix = ' with default temp root and auto dir generation on write.'

    @classmethod
    def mk_tmp_quick_store_path_format(cls, subpath=''):
        """Path of ``subpath`` under the class's folder (``_tmp_dirname``) in the system temp directory."""
        return mk_tmp_quick_store_dirpath(os.path.join(cls._tmp_dirname, subpath))

    def __init__(self, path_format=None, max_levels=None):
        if path_format is None:
            path_format = self.mk_tmp_quick_store_path_format()
            print(
                f'No path_format was given, so taking one from a tmp dir. Namely:\n\t{path_format}'
            )
        else:
            path_format = mk_absolute_path(path_format)
        super().__init__(path_format, max_levels=max_levels)


class QuickLocalStoreMixin(AutoMkPathformatMixin, AutoMkDirsOnSetitemMixin):
    """A mixin that will choose a path_format if none given,
    and will automatically create directories on setitem, when missing.
    """

    # _tmp_dirname = "quick_store"
    # _docsuffix = " with default temp root and auto dir generation on write."
    #
    # @classmethod
    # def mk_tmp_quick_store_path_format(cls, subpath=""):
    #     return mk_tmp_quick_store_dirpath(
    #         os.path.join(cls._tmp_dirname, subpath)
    #     )
    #
    # def __init__(self, path_format=None, max_levels=None):
    #     if path_format is None:
    #         path_format = self.mk_tmp_quick_store_path_format()
    #         print(
    #             f"No path_format was given, so taking one from a tmp dir. Namely:\n\t{path_format}"
    #         )
    #     else:
    #         path_format = mk_absolute_path(path_format)
    #     super().__init__(path_format, max_levels=max_levels)
    #
    # def __setitem__(self, k, v):
    #     dirname = os.path.dirname(os.path.join(self._prefix, k))
    #     os.makedirs(dirname, exist_ok=True)
    #     return super().__setitem__(k, v)


class QuickTextStore(QuickLocalStoreMixin, LocalTextStore):
    """``LocalTextStore`` with a temporary default root and directories created on write.

    >>> import os, tempfile
    >>> s = QuickTextStore(os.path.join(tempfile.mkdtemp(), 'sub'))
    >>> s['x/y.txt'] = 'z'  # sub/ and sub/x/ are created for you
    >>> list(s), s['x/y.txt']
    (['x/y.txt'], 'z')
    """


class QuickBinaryStore(QuickLocalStoreMixin, LocalBinaryStore):
    """``LocalBinaryStore`` with a temporary default root and directories created on write."""


class QuickJsonStore(SimpleJsonMixin, QuickTextStore):
    """``QuickTextStore`` whose values are read with ``json.loads`` and written with ``json.dumps``."""


class QuickPickleStore(QuickLocalStoreMixin, PickleStore):
    """``LocalPickleStore`` with a temporary default root and directories created on write.

    This is what ``QuickStore`` and ``LocalStore`` name. Without a ``path_format`` a folder
    under the system temp directory is used, and its path is printed.

    >>> import os, tempfile
    >>> s = QuickPickleStore(os.path.join(tempfile.mkdtemp(), 'quick'))
    >>> s['deep/er/key'] = [1, 2]
    >>> s['deep/er/key'], list(s)
    ([1, 2], ['deep/er/key'])
    """


QuickStore = QuickPickleStore  # alias
LocalStore = QuickStore  # alias


class DirStore(Store):
    """A store for local directories.
    Keys are directory names and values are subdirectory DirStores.

    >>> from py2store import __file__
    >>> import os
    >>> root = os.path.dirname(__file__)
    >>> s = DirStore(root)
    >>> assert set(s).issuperset({'stores', 'persisters', 'serializers', 'key_mappers'})
    """

    def __init__(self, rootdir):
        rootdir = ensure_slash_suffix(rootdir)
        super().__init__(store=DirReader(rootdir))
        self._prefix = rootdir

        key_wrap = PrefixRelativization(_prefix=rootdir)
        os_sep = os.sep
        self._id_of_key = lambda k: key_wrap._id_of_key(k) + os_sep
        self._key_of_id = lambda k: key_wrap._key_of_id(k)[:-1]

        # TODO: Look into alternatives for the raison d'etre of _new_node and _class_name
        # (They are there, because using self.__class__ directly goes to super)
        self.store._new_node = self.__class__
        self.store._class_name = self.__class__.__name__


class RelativeDirPathFormatKeys(PrefixRelativizationMixin, Store):
    """``DirpathFormatKeys`` (the folders under a root) wrapped in a ``Store`` with keys relative to the root."""

    @wraps(DirpathFormatKeys.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(store=DirpathFormatKeys(*args, **kwargs))
        self._prefix = self.store._prefix
