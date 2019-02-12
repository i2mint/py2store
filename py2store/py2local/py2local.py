import os
from typing import Callable
from glob import iglob

import attr

from i2i.py2store import file_sep
from i2i.py2store.py2store import Obj, Data
from i2i.py2store.py2store import PathOf, KeyValPersister, ObjStore


class FilepathOf(PathOf):
    """
    Transform a relative filename into an absolute path, optionally appending an extension.
    Note: No validation of the paths is carried out when transforming a key to a path. The transformation is purely
    a string transformation. The reverse key_of(path) function, on the other hand, will only return a key if
    the path has the expected ROOTDIR/key.EXT format (else, it will raise a ValueError)

    >>> filepath_of = FilepathOf(rootdir='ROOT', ext='.EXT')
    >>> filepath_of(key='name')
    'ROOT/name.EXT'
    >>> filepath_of.key_of(path='ROOT/name.EXT')  # get the key that would produce this path
    'name'
    >>> try:  # see that if we try to get the key for a path with a different root, that we get a ValueError
    ...     filepath_of.key_of('A_DIFFERENT_ROOT/name.EXT')
    ... except ValueError as e:
    ...     print(e)
    There is no key for path A_DIFFERENT_ROOT/name.EXT since the latter doesn't have the required ROOT/KEY.EXT format.
    >>> try:  # see that if we try to get the key for a path with a different ext, that we get a ValueError
    ...     filepath_of.key_of('ROOT/name.A_DIFFERENT_EXT')
    ... except ValueError as e:
    ...     print(e)
    There is no key for path ROOT/name.A_DIFFERENT_EXT since the latter doesn't have the required ROOT/KEY.EXT format.
    >>> # Without an ext...
    >>> filepath_of = FilepathOf('ROOT')
    >>> filepath_of('name')
    'ROOT/name'
    >>> filepath_of.key_of('ROOT/name')
    'name'
    >>> # Without a root
    >>> filepath_of = FilepathOf(ext='.EXT')
    >>> filepath_of('name')
    'name.EXT'
    >>> filepath_of.key_of('name.EXT')
    'name'
    """

    def __init__(self, rootdir: str = '', ext: str = ''):
        """
        Make a callable that will transform a relative filename to an absolute one.
        :param rootdir: The root directory
        :param ext: The extension to append systematically. Note that the function will not check if an extension is
            already given.
        >>>
        """
        if rootdir.endswith(os.path.sep):
            rootdir = rootdir[:-1]  # remove the trailing slash
        self.rootdir = rootdir
        if ext:
            if not ext.startswith('.'):
                ext = '.' + ext
        self.ext = ext or ''  # just in case someone says ext=True or ext=None

    def __call__(self, key):
        """
        Get the path corresponding to this key.
        :param key: A string
        :return:
        >>> filepath_of = FilepathOf('ROOT', '.EXT')
        >>> filepath_of(key='name')
        'ROOT/name.EXT'
        """
        return os.path.join(self.rootdir, key) + self.ext

    def key_of(self, path):
        """
        Inverse of the __call__ method: Will return the key that would produce the given path, or raise a ValueError if
        there's no such key (which happens if path does not have the expected ROOTDIR/key.EXT format)
        :param path: A string that should have the ROOT/KEY.EXT format
        :return The KEY
        >>> filepath_of = FilepathOf('ROOT', '.EXT')
        >>> filepath_of(key='name')
        'ROOT/name.EXT'
        >>> filepath_of.key_of(path='ROOT/name.EXT')  # get the key that would produce this path
        'name'
        """
        dirpath, basename = os.path.split(path)
        if dirpath == self.rootdir:
            name, ext = os.path.splitext(basename)
            if ext == self.ext:
                return name
        raise ValueError("There is no key for path {} "
                         "since the latter doesn't have the required {} format.".format(path, self('KEY')))
        # in all other cases return None


########################################################################################################################
# Local Storage

@attr.s
class IterableDirMixin(object):
    rootdir = attr.ib(default='')
    ext = attr.ib(default='')

    def __iter__(self):
        return iglob('{}{}*{}'.format(self.rootdir, file_sep, self.ext))


class LocalFileDeletionMixin(object):
    """
    Class that is meant to be used to define the delete method of a subclass as the local file delete
    Note: Most of the time, should be included as the first super class, or at least before any other class
    that might define a delete method (or else, subclassing LocalFileDeletionMixin will have no effect)
    """
    delete = staticmethod(os.remove)


@attr.s
class LocalKeyValPersister(LocalFileDeletionMixin, KeyValPersister, IterableDirMixin):
    file_write_mode = attr.ib(default='w')
    file_read_mode = attr.ib(default='r')

    def dump(self, data: Data, path: str):
        with open(path, self.file_write_mode) as fp:
            fp.write(data)

    def load(self, path: str):
        with open(path, self.file_read_mode) as fp:
            data = fp.read()
        return data


def mk_local_persister(rootdir: str,
                       ext: str = '',
                       file_write_mode='w',
                       file_read_mode='r',
                       mkdir=False):
    """
    Make a data store that works with local files.

    :param rootdir: root directory where data should be stored
    :param ext: extension that
    :param file_write_mode:
    :param file_read_mode:
    :return:
    >>> import os
    >>> from tempfile import gettempdir
    >>>
    >>> rootdir = os.path.join(gettempdir(), 'doctest_dir')  # mk and get a temporary folder to work with
    >>> if not os.path.exists(rootdir):
    ...     os.mkdir(rootdir)
    >>> ext = '.ext'
    >>> f = lambda key: os.path.join(rootdir, key) + ext  # a util function to make paths with rootdir and ext
    >>> # make a data store
    >>> persister = mk_local_persister(rootdir, ext)
    >>> # and dump two items in it
    >>> persister.dump('3', f('three'))
    >>> persister.dump('[1, 2, 3]', f('a_list'))
    >>>
    >>> [os.path.basename(path) for path in persister]
    ['a_list.ext', 'three.ext']
    >>> # loading the data we put in three.ext:
    >>> persister.load(f('three'))
    '3'
    >>> # replacing what's in three.ext
    >>> persister.dump('not_3_any_more', f('three'))
    >>> persister.load(f('three'))
    'not_3_any_more'
    >>> # deleting what's in three.ext
    >>> persister.delete(f('three'))
    >>> # ... and showing that we can't load it anymore
    >>> try:
    ...     persister.load(f('three'))
    ... except Exception as err:
    ...     print("Indeed, you should have an exception, since this file doesn't exist anymore")
    ...
    Indeed, you should have an exception, since this file doesn't exist anymore
    """
    file_sep = os.path.sep
    if rootdir.endswith(file_sep):
        rootdir = rootdir[:-1]
    if mkdir and not os.path.exists(rootdir):
        os.mkdir(rootdir)
    persister = LocalKeyValPersister(rootdir, ext, file_write_mode, file_read_mode)
    return persister


def mk_local_obj_store(rootdir: str,
                       ext: str = '',
                       data_of_obj: Callable[[Obj], Data] = lambda obj: obj,
                       obj_of_data: Callable[[Data], Obj] = lambda data: data,
                       file_write_mode='w',
                       file_read_mode='r'
                       ):
    """

    :param rootdir:
    :param ext:
    :param data_of_obj:
    :param obj_of_data:
    :param file_write_mode:
    :param file_read_mode:
    :return:
    """
    filepath_of = FilepathOf(rootdir=rootdir, ext=ext)

    persister = mk_local_persister(rootdir, ext, file_write_mode, file_read_mode)

    return ObjStore(persister=persister,
                    path_of=filepath_of,
                    data_of_obj=data_of_obj,
                    obj_of_data=obj_of_data)


########################################################################################################################
# Pickle Serializer
def mk_local_pickle_obj_store(rootdir: str, ext: str = '', protocol=None, fix_imports=True):
    import pickle
    def serial_of_obj(obj):
        return pickle.dumps(obj, protocol=protocol, fix_imports=fix_imports)

    def obj_of_serial(serial):
        return pickle.loads(serial, protocol=protocol, fix_imports=fix_imports)

    # Notice that file_write_mode and file_read_mode defaults are overwritten to binary mode
    return mk_local_obj_store(rootdir=rootdir, ext=ext,
                              data_of_obj=serial_of_obj, obj_of_data=obj_of_serial,
                              file_write_mode='bw', file_read_mode='br')
