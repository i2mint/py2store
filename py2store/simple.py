"""
This standalone module is meant to demonstrate the functionality of py2store without all the bells and whistles,
annotations, comments, heavy documentation, doc tests, etc.

In this module you'll see how one can have the key-value interface of a MutableMapping (thing dicts), but control
where the data is actually stored (persister), how objects are serialized, and how they're referenced.

The main classes to check out are:
* DictPickleStore: In-memory 'storage' (using a dict as a persister) that stores the pickles of objects.
* SimpleFileStore: Uses local files to store (text or binary) data, using relative paths as keys, enforcing a root
    directory, and listing only items under that directory.
* PickleFileStore: A SimpleFileStore, but stores all objects as pickles
And just to show something a bit more complex, we also include:
* S3Store: Like SimpleFileStore, but stores data in an AWS S3 bucket.

pytest included

"""

########################################################################################################################
# Base classes
from collections.abc import MutableMapping


class Persister(MutableMapping):
    """ Interface for a StoreBase
    Essentially, a MutableMapping where __len__ is taken by counting how many elements __iter__ yields,
    and where clear is overridden to raise a NotImplementedError (to protect from bulk deletion).
    """

    def __len__(self):
        count = 0
        for _ in self.__iter__():
            count += 1
        return count

    def clear(self):
        raise NotImplementedError('''
        The clear method was overridden to make dangerous difficult.
        If you really want to delete all your data, you can do so by doing:
            try:
                while True:
                    self.popitem()
            except KeyError:
                pass''')


class Store:
    """
    By store we mean key-value store. This could be files in a filesystem, objects in s3, or a database. Where and
    how the content is stored should be specified, but StoreInterface offers a dict-like interface to this.

    __getitem__ calls: _id_of_key			                    _obj_of_data
    __setitem__ calls: _id_of_key		        _data_of_obj
    __delitem__ calls: _id_of_key
    __iter__    calls:	            _key_of_id
    """

    def __init__(self,
                 persister=None,
                 _id_of_key=lambda x: x,
                 _key_of_id=lambda x: x,
                 _data_of_obj=lambda x: x,
                 _obj_of_data=lambda x: x):
        if persister is None:
            persister = dict()
        self.persister = persister
        self._id_of_key = _id_of_key
        self._key_of_id = _key_of_id
        self._data_of_obj = _data_of_obj
        self._obj_of_data = _obj_of_data

    def __getitem__(self, k):
        return self._obj_of_data(self.persister.__getitem__(self._id_of_key(k)))

    def __setitem__(self, k, v):
        return self.persister.__setitem__(self._id_of_key(k), self._data_of_obj(v))

    def __delitem__(self, k):
        return self.persister.__delitem__(self._id_of_key(k))

    def __iter__(self):
        return map(self._key_of_id, self.persister.__iter__())

    def __len__(self):
        return self.persister.__len__()

    def __contains__(self, k):
        return self.persister.__contains__(self._id_of_key(k))


########################################################################################################################
# Utils
class PrefixRelativization:
    """A key wrap that allows one to interface with absolute paths through relative paths.
    The original intent was for local files. Instead of referencing files through an absolute path such as
        /A/VERY/LONG/ROOT/FOLDER/the/file/we.want
    we can instead reference the file as
        the/file/we.want

    But PrefixRelativization can be used, not only for local paths, but when ever a string reference is involved.
    In fact, not only strings, but any key object that has a __len__, __add__, and subscripting.
    """

    def __init__(self, _prefix=""):
        self._prefix = _prefix

    @property
    def _prefix_length(self):
        return len(self._prefix)

    def _id_of_key(self, k):
        return self._prefix + k

    def _key_of_id(self, _id):
        return _id[self._prefix_length:]


import pickle


class PickleValWrap:
    """A val wrap that serializes by pickling objects."""

    def __init__(self, protocol=None, fix_imports=True):
        self.protocol = protocol
        self.fix_imports = fix_imports

    def _data_of_obj(self, v):
        return pickle.dumps(v, protocol=self.protocol, fix_imports=self.fix_imports)

    def _obj_of_data(self, v):
        return pickle.loads(v, fix_imports=self.fix_imports)


########################################################################################################################
########################################################################################################################
# Dict store

from collections import UserDict


class DictPersister(Persister, UserDict):
    pass


class DictPickleStore(Store):
    """Completely useless store on it's own since a dict can store python objects as is, so
    there's no need to pickle the objects to store them.
    Yet, this store exists to demonstrate how we can mix a persister and a val wrap"""

    def __init__(self, protocol=None, fix_imports=True):
        persister = DictPersister()
        val_wrap = PickleValWrap(protocol=protocol, fix_imports=fix_imports)
        super().__init__(persister=persister, _data_of_obj=val_wrap._data_of_obj, _obj_of_data=val_wrap._obj_of_data)


########################################################################################################################
########################################################################################################################
# Local Files
import os
import re
from glob import iglob

########################################################################################################################
# File system navigation: Utils

file_sep = os.sep


class KeyValidationError(ValueError):
    """Error to raise when a key is not valid"""
    pass


def ensure_slash_suffix(path):
    if not path.endswith(file_sep):
        return path + file_sep
    else:
        return path


def filepaths_in_dir(rootdir):
    return iglob(ensure_slash_suffix(rootdir) + '*')


def iter_filepaths_in_folder_recursively(root_folder):
    for full_path in filepaths_in_dir(root_folder):
        if os.path.isdir(full_path):
            for entry in iter_filepaths_in_folder_recursively(full_path):
                yield entry
        else:
            if os.path.isfile(full_path):
                yield full_path


########################################################################################################################
# Local File StoreBase

class SimpleFilePersister(Persister):
    """Read/write (text or binary) data to files under a given rootdir.
    Keys must be absolute file paths.
    Paths that don't start with rootdir will be raise a KeyValidationError
    """

    def __init__(self, rootdir, mode='t'):
        self.rootdir = ensure_slash_suffix(rootdir)
        assert mode in {'t', 'b', ''}, f"mode ({mode}) not valid: Must be 't' or 'b'"
        self.mode = mode

    def _is_valid_key(self, k):
        return k.startswith(self.rootdir)

    def _validate_key(self, k):
        if not self._is_valid_key(k):
            raise KeyValidationError(f"Path ({k}) not valid. Must begin with {self.rootdir}")

    def __getitem__(self, k):
        self._validate_key(k)
        with open(k, 'r' + self.mode) as fp:
            data = fp.read()
        return data

    def __setitem__(self, k, v):
        self._validate_key(k)
        with open(k, 'w' + self.mode) as fp:
            fp.write(v)

    def __delitem__(self, k):
        self._validate_key(k)
        os.remove(k)

    def __contains__(self, k):
        self._validate_key(k)
        return os.path.isfile(k)

    def __iter__(self):
        yield from filter(self._is_valid_key, iter_filepaths_in_folder_recursively(self.rootdir))


########################################################################################################################
# Local File Stores
class SimpleFileStore(Store):
    """A simple local file store that stores (either as text or as binary) under a root directory, with access
    keys expressed in relative paths.
    """

    def __init__(self, rootdir, mode='t'):
        rootdir = ensure_slash_suffix(rootdir)
        persister = SimpleFilePersister(rootdir, mode)
        key_wrap = PrefixRelativization(_prefix=rootdir)
        super().__init__(persister=persister, _id_of_key=key_wrap._id_of_key, _key_of_id=key_wrap._key_of_id)


class PickleFileStore(Store):
    """A simple local file store that stores (either as text or as binary) under a root directory, with access
    keys expressed in relative paths.
    """

    def __init__(self, rootdir, mode='b', protocol=None, fix_imports=True):
        rootdir = ensure_slash_suffix(rootdir)
        persister = SimpleFilePersister(rootdir, mode)
        key_wrap = PrefixRelativization(_prefix=rootdir)
        val_wrap = PickleValWrap(protocol=protocol, fix_imports=fix_imports)
        super().__init__(persister=persister,
                         _id_of_key=key_wrap._id_of_key, _key_of_id=key_wrap._key_of_id,
                         _data_of_obj=val_wrap._data_of_obj, _obj_of_data=val_wrap._obj_of_data)


########################################################################################################################
########################################################################################################################
# S3

from functools import partial
from botocore.client import Config
from botocore.exceptions import ClientError
import boto3


class NoSuchKeyError(KeyError):
    pass


encode_as_utf8 = partial(str, encoding='utf-8')

DFLT_S3_OBJ_OF_DATA = encode_as_utf8
DFLT_AWS_S3_ENDPOINT = "https://s3.amazonaws.com"
DFLT_BOTO_CLIENT_VERIFY = None
DFLT_SIGNATURE_VERSION = 's3v4'
DFLT_CONFIG = Config(signature_version=DFLT_SIGNATURE_VERSION)


def get_s3_resource(aws_access_key_id,
                    aws_secret_access_key,
                    endpoint_url=DFLT_AWS_S3_ENDPOINT,
                    verify=DFLT_BOTO_CLIENT_VERIFY,
                    config=DFLT_CONFIG):
    """
    Get boto3 s3 resource.
    :param aws_access_key_id:
    :param aws_secret_access_key:
    :param endpoint_url:
    :param verify:
    :param signature_version:
    :return:
    """
    return boto3.resource('s3',
                          endpoint_url=endpoint_url,
                          aws_access_key_id=aws_access_key_id,
                          aws_secret_access_key=aws_secret_access_key,
                          verify=verify,
                          config=config)


class S3BucketPersister(Persister):
    def __init__(self, bucket_name: str, _s3_bucket, _prefix: str = ''):
        self.bucket_name = bucket_name
        self._s3_bucket = _s3_bucket
        self._prefix = _prefix

    def __getitem__(self, k):
        try:
            return k.get()['Body'].read()
        except Exception as e:
            raise NoSuchKeyError("Key wasn't found: {}".format(k))

    def __setitem__(self, k, v):
        k.put(Body=v)

    def __delitem__(self, k):
        try:
            k.delete()
        except Exception as e:
            if hasattr(e, '__name__'):
                if e.__name__ == 'NoSuchKey':
                    raise NoSuchKeyError("Key wasn't found: {}".format(k))
            raise  # if you got so far

    def __iter__(self):
        return iter(self._s3_bucket.objects.filter(Prefix=self._prefix))

    def __contains__(self, k):
        try:
            k.load()
            return True  # if all went well
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise

    @classmethod
    def from_s3_resource_kwargs(cls, bucket_name, _prefix: str = '', **kwargs):
        s3_resource = get_s3_resource(**kwargs)
        return cls.from_s3_resource(bucket_name, s3_resource, _prefix=_prefix)

    @classmethod
    def from_s3_resource(cls,
                         bucket_name,
                         s3_resource,
                         _prefix=''
                         ):
        s3_bucket = s3_resource.Bucket(bucket_name)
        return cls(bucket_name, s3_bucket, _prefix=_prefix)


class S3Store(Store):
    def __init__(self, bucket_name: str, _s3_bucket, _prefix: str = '',
                 _data_of_obj=lambda x: x, _obj_of_data=DFLT_S3_OBJ_OF_DATA):
        persister = S3BucketPersister(bucket_name, _s3_bucket, _prefix)
        key_wrap = PrefixRelativization(_prefix=persister._prefix)

        def _id_of_key(k):
            """Gets an 's3 bucket object' for a corresponding string key"""
            return persister._s3_bucket.Object(key=key_wrap._id_of_key(k))

        def _key_of_id(_id):  # transforms a string key into an s3 object
            """Gets the string key of a 's3 bucket object'"""
            return key_wrap._key_of_id(_id.key)

        super().__init__(persister=persister,
                         _id_of_key=_id_of_key,
                         _key_of_id=_key_of_id,
                         _data_of_obj=_data_of_obj,
                         _obj_of_data=_obj_of_data
                         )

    @classmethod
    def from_s3_resource_kwargs(cls,
                                bucket_name,
                                _prefix: str = '',
                                _data_of_obj=lambda x: x,
                                _obj_of_data=DFLT_S3_OBJ_OF_DATA,
                                **kwargs
                                ):
        s3_resource = get_s3_resource(**kwargs)
        return cls.from_s3_resource(bucket_name, s3_resource, _prefix=_prefix,
                                    _data_of_obj=_data_of_obj, _obj_of_data=_obj_of_data)

    @classmethod
    def from_s3_resource(cls, bucket_name, s3_resource, **kwargs):
        s3_bucket = s3_resource.Bucket(bucket_name)
        return cls(bucket_name, s3_bucket, **kwargs)


########################################################################################################################
########################################################################################################################
# Testing functions
class OperationNotAllowed(NotImplementedError):
    pass


class DeletionsNotAllowed(OperationNotAllowed):
    pass


class OverWritesNotAllowedError(OperationNotAllowed):
    """Error to raise when a key is not valid"""
    pass


def _delete_keys_from_store(store, keys_to_delete):
    for k in keys_to_delete:
        if k in store:  # if key already in s, delete it
            del store[k]


def _test_ops_on_store(store):
    s = store  # just to be able to use shorthand "s"

    _delete_keys_from_store(s, ['_foo', '_hello', '_non_existing_key_'])

    # test "not in"
    assert '_non_existing_key_' not in s, \
        "I really wasn't expecting that key to be in there!"

    s['_foo'] = 'bar'  # store 'bar' in '_foo'
    assert "_foo" in s, '"_foo" in s'
    assert s['_foo'] == 'bar'

    s['_hello'] = 'world'  # store 'world' in '_hello'

    if hasattr(s, 'keys'):
        assert set(s.keys()).issuperset({'_foo', '_hello'})
    if hasattr(s, 'values'):
        assert set(s.values()).issuperset({'bar', 'world'})
    if hasattr(s, 'items'):
        assert set(s.items()).issuperset({('_foo', 'bar'), ('_hello', 'world')})
    if hasattr(s, 'get'):
        assert s.get('_hello') == 'world'
        assert s.get('_non_existing_key_', 'some default') == 'some default'
        assert s.get('_non_existing_key_', None) is None
    if hasattr(s, 'setdefault'):
        assert s.setdefault('_hello', 'this_will_never_be_used') == 'world'
        assert s.setdefault('_non_existing_key_', 'this_will') == 'this_will'
        assert s['_non_existing_key_'] == 'this_will'
        del s['_non_existing_key_']

    # test "not in" when there's something
    assert '_non_existing_key_' not in s, \
        "I really wasn't expecting that key to be in there!"

    # wraped in try/except in case deleting is not allowed
    try:
        # testing deletion
        del s['_hello']  # delet _hello
        assert '_hello' not in s
        s['_hello'] = 'world'  # put it back

        if hasattr(s, 'pop'):
            v = s.pop('_hello')
            assert v == 'world'
            assert '_hello' not in s
            s['_hello'] = 'world'  # put it back
    except DeletionsNotAllowed:
        pass

    # wraped in try/except in case overwriting is not allowed
    try:
        s['_foo'] = 'a different value'
        assert s['_foo'] == 'a different value'
    except OverWritesNotAllowedError:
        pass

    _delete_keys_from_store(s, ['_foo', '_hello'])


def _test_len(store):
    s = store  # just to be able to use shorthand "s"

    _delete_keys_from_store(s, ['_foo', '_hello'])

    n = len(s)  # remember how many items there are

    s['_foo'] = 'bar'  # store 'bar' in '_foo'
    assert len(s) == n + 1, "You should have an extra item in the store"

    s['_hello'] = 'world'  # store 'world' in '_hello'
    assert len(s) == n + 2, "You should have had two extra items in the store"

    try:
        # testing deletion
        del s['_hello']  # delet _hello
        assert len(s) == n + 1
        s['_hello'] = 'world'  # put it back

        if hasattr(s, 'pop'):
            _ = s.pop('_hello')
            assert len(s) == n + 1
            s['_hello'] = 'world'  # put it back
    except DeletionsNotAllowed:
        pass

    # wraped in try/except in case overwriting is not allowed
    try:
        s['_foo'] = 'a different value'
        assert len(s) == n + 2
    except OverWritesNotAllowedError:
        pass

    _delete_keys_from_store(s, ['_foo', '_hello'])


def _multi_test(store):
    _test_ops_on_store(store)
    _test_len(store)


def test_dict_ops():
    store = dict()
    _multi_test(store)


def test_local_file_ops():
    store = DictPickleStore()
    _multi_test(store)

    import os
    import shutil
    from tempfile import gettempdir

    rootdir = os.path.join(gettempdir(), 'py_store_tests')
    # empty and recreate rootdir if necessary
    if os.path.isdir(rootdir):
        shutil.rmtree(rootdir)
    os.mkdir(rootdir)

    store = SimpleFileStore(rootdir=rootdir)
    _multi_test(store)

    store = PickleFileStore(rootdir=rootdir)
    _multi_test(store)


if __name__ == '__main__':
    import pytest

    pytest.main()
