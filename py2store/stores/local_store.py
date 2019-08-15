import os
import pickle
from functools import partial, wraps
from warnings import warn

from py2store.base import Store, Persister
from py2store.core import PrefixRelativizationMixin
from py2store.persisters.local_files import PathFormatPersister, DirpathFormatKeys


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


class RelativePathFormatStore(PrefixRelativizationMixin, Store):
    """Local file store using templated relative paths.
    """
    @wraps(PathFormatStore.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(store=PathFormatStore(*args, **kwargs))
        self._prefix = self.store._prefix


class RelativePathFormatStoreEnforcingFormat(RelativePathFormatStore):
    """A RelativePathFormatStore, but that won't allow one to use a key that is not valid
    (according to the self.store.is_valid_key boolean method).
    """

    def _id_of_key(self, k):
        _id = super()._id_of_key(k)
        if self.store.is_valid_key(_id):
            return _id
        else:
            raise ValueError(f"Key not valid: {k}")


class MakeMissingDirsStoreMixin:
    """Will make a local file store automatically create the directories needed to create a file.
    Should be placed before the concrete perisister in the mro but in such a manner so that it receives full paths.
    """

    def __setitem__(self, k, v):
        _id = self._id_of_key(k)
        dirname = os.path.dirname(_id)
        os.makedirs(dirname, exist_ok=1)
        super().__setitem__(k, v)


class RelativeDirPathFormatKeys(PrefixRelativizationMixin, Store):
    @wraps(DirpathFormatKeys.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(store=DirpathFormatKeys(*args, **kwargs))
        self._prefix = self.store._prefix


class PathFormatStoreWithPrefix(Store):
    @wraps(PathFormatStore.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(store=PathFormatStore(*args, **kwargs))
        self._prefix = self.store._prefix


class RelativePathFormatStore2(PrefixRelativizationMixin, PathFormatStoreWithPrefix):
    pass


class LocalTextStore(RelativePathFormatStore):
    def __init__(self, path_format):
        super().__init__(path_format, mode='t')


class LocalBinaryStore(RelativePathFormatStore):
    def __init__(self, path_format):
        super().__init__(path_format, mode='b')


class PickleStore(RelativePathFormatStore):
    """
    A local files pickle store
    """

    def __init__(self, path_format,
                 fix_imports=True, protocol=None, pickle_encoding='ASCII', pickle_errors='strict',
                 **open_kwargs):
        super().__init__(path_format, mode='b', **open_kwargs)
        self._loads = partial(pickle.loads, fix_imports=fix_imports, encoding=pickle_encoding, errors=pickle_errors)
        self._dumps = partial(pickle.dumps, protocol=protocol, fix_imports=fix_imports)

    def __getitem__(self, k):
        return self._loads(super().__getitem__(k))

    def __setitem__(self, k, v):
        return super().__setitem__(k, self._dumps(v))


def mk_tmp_quick_store_dirpath(dirname=''):
    from tempfile import gettempdir
    temp_root = gettempdir()
    return os.path.join(temp_root, dirname)


class QuickStore(PickleStore):
    """Make a quick persisting store with minimal (or no) further specification.
    Will persist in the local file system using relative paths and pickle to serialize.
    If directories in the path don't exist, they're made automatically.
    If the root directory for the store isn't given, you'll be given one (but it will be a temporary folder).
    """

    def __init__(self, path_format=None):
        if path_format is None:
            path_format = mk_tmp_quick_store_dirpath('quick_store')
            warn(f"No path_format was given, so taking one from a tmp dir. Namely:\n\t{path_format}")
        super().__init__(path_format)

    def __setitem__(self, k, v):
        dirname = os.path.dirname(os.path.join(self._prefix, k))
        os.makedirs(dirname, exist_ok=1)
        super().__setitem__(k, v)


LocalStore = QuickStore  # alias
