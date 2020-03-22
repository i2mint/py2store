import os
from functools import wraps

from py2store.base import Store, Persister
from py2store.core import PrefixRelativizationMixin, PrefixRelativization
from py2store.key_mappers.paths import mk_relative_path_store
from py2store.serializers.pickled import mk_pickle_rw_funcs
from py2store.persisters.local_files import PathFormatPersister, DirpathFormatKeys, DirReader, ensure_slash_suffix
from py2store.persisters.local_files import DirCollection
from py2store.mixins import SimpleJsonMixin


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
    >>> assert list(s) == [filepath_of('a'), filepath_of('b')]  # there's two files in s
    >>> filepath_of('a') in s  # rootdir/a is in s
    True
    >>> filepath_of('not_there') in s  # rootdir/not_there is not in s
    False
    >>> filepath_of('not_there') not in s  # rootdir/not_there is not in s
    True
    >>> assert list(s.keys()) == [filepath_of('a'), filepath_of('b')]  # the keys (filepaths) of s
    >>> sorted(list(s.values())) # the values of s (contents of files)
    ['bar', 'foo']
    >>> assert list(s.items()) == [(filepath_of('a'), 'foo'), (filepath_of('b'), 'bar')]  # the (path, content) items
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


RelPathLocalFileStore = mk_relative_path_store(PathFormatPersister, name='RelPathLocalFileStore')
RelPathLocalFileStore.__doc__ = """Local file store using templated relative paths."""

RelPathLocalFileStoreEnforcingFormat = mk_relative_path_store(PathFormatPersister,
                                                              name='RelPathLocalFileStoreEnforcingFormat')
RelPathLocalFileStoreEnforcingFormat.__doc__ = \
    """A RelativePathFormatStore, but that won't allow one to use a key that is not valid 
    (according to the self.store.is_valid_key boolean method)"""

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


class MakeMissingDirsStoreMixin:
    """Will make a local file store automatically create the directories needed to create a file.
    Should be placed before the concrete perisister in the mro but in such a manner so that it receives full paths.
    """

    def __setitem__(self, k, v):
        _id = self._id_of_key(k)
        dirname = os.path.dirname(_id)
        os.makedirs(dirname, exist_ok=1)
        super().__setitem__(k, v)


class PathFormatStoreWithPrefix(Store):
    @wraps(PathFormatStore.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(store=PathFormatStore(*args, **kwargs))
        self._prefix = self.store._prefix


# Would like to replace the above pattern with what's below, but
# from py2store.trans import store_wrap
# PathFormatStoreWithPrefix = store_wrap(PathFormatStore, 'PathFormatStoreWithPrefix')


class RelativePathFormatStore2(PrefixRelativizationMixin, PathFormatStoreWithPrefix):
    pass


class LocalTextStore(RelativePathFormatStore):
    """Local files store for text data"""

    def __init__(self, path_format, max_levels=None):
        super().__init__(path_format, max_levels=max_levels, mode='t')


class LocalBinaryStore(RelativePathFormatStore):
    """Local files store for binary data"""

    def __init__(self, path_format, max_levels=None):
        super().__init__(path_format, max_levels=max_levels, mode='b')


class LocalPickleStore(RelativePathFormatStore):
    """Local files store with pickle serialization"""

    def __init__(self, path_format, max_levels=None,
                 fix_imports=True, protocol=None, pickle_encoding='ASCII', pickle_errors='strict',
                 **open_kwargs):
        super().__init__(path_format, max_levels=max_levels, mode='b', **open_kwargs)
        self._loads, self._dumps = mk_pickle_rw_funcs(fix_imports, protocol, pickle_encoding, pickle_errors)

    @classmethod
    def for_dill(cls, path_format, max_levels=None, open_kwargs=None, *args, **kwargs):
        from py2store.serializers.pickled import mk_dill_rw_funcs
        open_kwargs = open_kwargs or {}
        self = cls(path_format, max_levels=max_levels, **open_kwargs)
        self._loads, self._dumps = mk_dill_rw_funcs(*args, **kwargs)
        return self

    def __getitem__(self, k):
        return self._loads(super().__getitem__(k))

    def __setitem__(self, k, v):
        return super().__setitem__(k, self._dumps(v))

    # TODO: hack to take care of problem with head not playing well with wrappers. Find better solution.
    def head(self):
        for k, v in self.items():
            return k, v


class LocalJsonStore(SimpleJsonMixin, LocalTextStore):
    __doc__ = str(LocalTextStore.__doc__) + SimpleJsonMixin._docsuffix


PickleStore = LocalPickleStore  # alias


def mk_tmp_quick_store_dirpath(dirname=''):
    from tempfile import gettempdir
    temp_root = gettempdir()
    return os.path.join(temp_root, dirname)


def mk_absolute_path(path_format):
    if path_format.startswith('~'):
        path_format = os.path.expanduser(path_format)
    elif path_format.startswith('.'):
        path_format = os.path.abspath(path_format)
    return path_format


class QuickLocalStoreMixin:
    """A mixin that will choose a path_format if none given, and will create directories under the (temp) root,
    at write time, as needed.
    """

    _tmp_dirname = 'quick_store'
    _docsuffix = ' with default temp root and auto dir generation on write.'

    @classmethod
    def mk_tmp_quick_store_path_format(cls, subpath=''):
        return mk_tmp_quick_store_dirpath(os.path.join(cls._tmp_dirname, subpath))

    def __init__(self, path_format=None, max_levels=None):
        if path_format is None:
            path_format = self.mk_tmp_quick_store_path_format()
            print(f"No path_format was given, so taking one from a tmp dir. Namely:\n\t{path_format}")
        else:
            path_format = mk_absolute_path(path_format)
        super().__init__(path_format, max_levels=max_levels)

    def __setitem__(self, k, v):
        dirname = os.path.dirname(os.path.join(self._prefix, k))
        os.makedirs(dirname, exist_ok=1)
        return super().__setitem__(k, v)


class QuickTextStore(QuickLocalStoreMixin, LocalTextStore):
    __doc__ = str(LocalTextStore.__doc__) + QuickLocalStoreMixin._docsuffix


class QuickBinaryStore(QuickLocalStoreMixin, LocalBinaryStore):
    __doc__ = str(LocalBinaryStore.__doc__) + QuickLocalStoreMixin._docsuffix


class QuickJsonStore(SimpleJsonMixin, QuickTextStore):
    __doc__ = str(QuickTextStore.__doc__) + SimpleJsonMixin._docsuffix


class QuickPickleStore(QuickLocalStoreMixin, PickleStore):
    __doc__ = str(PickleStore.__doc__) + QuickLocalStoreMixin._docsuffix


QuickStore = QuickPickleStore  # alias
LocalStore = QuickStore  # alias


class DirStore(Store):
    """
    Store whose keys are directory names and values are subdirectory names.

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
        self._id_of_key = lambda k: key_wrap._id_of_key(k) + os.sep
        self._key_of_id = lambda k: key_wrap._key_of_id(k)[:-1]

        # TODO: Look into alternatives for the raison d'etre of _new_node and _class_name
        # (They are there, because using self.__class__ directly goes to super)
        self.store._new_node = self.__class__
        self.store._class_name = self.__class__.__name__


class RelativeDirPathFormatKeys(PrefixRelativizationMixin, Store):
    @wraps(DirpathFormatKeys.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(store=DirpathFormatKeys(*args, **kwargs))
        self._prefix = self.store._prefix
