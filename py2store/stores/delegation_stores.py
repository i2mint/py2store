from collections.abc import MutableMapping

from py2store.errors import KeyValidationError
from py2store.util import lazyprop


# TODO: Define store type so the type is defined by it's methods, not by subclassing.
class Persister(MutableMapping):
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


# TODO: Make identity_func "identifiable". If we use the following one, we can use == to detect it's use,
# TODO: ... but there may be a way to annotate, register, or type any identity function so it can be detected.
def identity_func(x):
    return x


class Store(Persister):
    """
    By store we mean key-value store. This could be files in a filesystem, objects in s3, or a database. Where and
    how the content is stored should be specified, but StoreInterface offers a dict-like interface to this.

    __getitem__ calls: _id_of_key			                    _obj_of_data
    __setitem__ calls: _id_of_key		        _data_of_obj
    __delitem__ calls: _id_of_key
    __iter__    calls:	            _key_of_id
    """

    # __slots__ = ('_id_of_key', '_key_of_id', '_data_of_obj', '_obj_of_data')

    # _id_of_key = lambda x: x
    # _key_of_id = lambda x: x
    # _data_of_obj = lambda x: x
    # _obj_of_data = lambda x: x

    def __init__(self,
                 store=None,
                 _id_of_key=identity_func,
                 _key_of_id=identity_func,
                 _data_of_obj=identity_func,
                 _obj_of_data=identity_func):
        if store is None:
            store = dict()
        self.store = store
        self._id_of_key = _id_of_key
        self._key_of_id = _key_of_id
        self._data_of_obj = _data_of_obj
        self._obj_of_data = _obj_of_data

    # Read ####################################################################
    def __getitem__(self, k):
        return self._obj_of_data(self.store.__getitem__(self._id_of_key(k)))

    def get(self, k, default=None):
        self.store.get(self._id_of_key(k), default=default)

    # Explore ####################################################################
    def __iter__(self):
        return map(self._key_of_id, self.store.__iter__())

    def __len__(self):
        return self.store.__len__()

    def __contains__(self, k):
        return self.store.__contains__(self._id_of_key(k))

    # Write ####################################################################
    def __setitem__(self, k, v):
        return self.store.__setitem__(self._id_of_key(k), self._data_of_obj(v))

    # Delete ####################################################################
    def __delitem__(self, k):
        return self.store.__delitem__(self._id_of_key(k))

    def clear(self):
        raise NotImplementedError('''
        The clear method was overridden to make dangerous difficult.
        If you really want to delete all your data, you can do so by doing:
            try:
                while True:
                    self.popitem()
            except KeyError:
                pass''')


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

    @lazyprop
    def _prefix_length(self):
        return len(self._prefix)

    def _id_of_key(self, k):
        return self._prefix + k

    def _key_of_id(self, _id):
        return _id[self._prefix_length:]


# class LocalFilePersister(FilepathFormatKeys, LocalFileRWD):
#     pass


########################################################################################################################
########################################################################################################################
# Local Files
import os
import re
from glob import iglob

########################################################################################################################
# File system navigation: Utils

file_sep = os.sep


def ensure_slash_suffix(path):
    if not path.endswith(file_sep):
        return path + file_sep
    else:
        return path


def pattern_filter(pattern):
    pattern = re.compile(pattern)

    def _pattern_filter(s):
        return pattern.match(s) is not None

    return _pattern_filter


def iter_relative_files_and_folder(root_folder):
    root_folder = ensure_slash_suffix(root_folder)
    return map(lambda x: x.replace(root_folder, ''), iglob(root_folder + '*'))


def iter_filepaths_in_folder(root_folder):
    return (os.path.join(root_folder, name) for name in iter_relative_files_and_folder(root_folder))


def iter_filepaths_in_folder_recursively(root_folder):
    for full_path in iter_filepaths_in_folder(root_folder):
        if os.path.isdir(full_path):
            for entry in iter_filepaths_in_folder_recursively(full_path):
                yield entry
        else:
            if os.path.isfile(full_path):
                yield full_path


########################################################################################################################
# Local File stores

class SimpleFilePersister(Persister):
    def __init__(self, rootdir, mode='t'):
        self.rootdir = ensure_slash_suffix(rootdir)
        assert mode in {'t', 'b', ''}, f"mode ({mode}) not valid: Must be 't' or 'b'"
        self.mode = mode

    def _validate_key(self, k):
        if not k.startswith(self.rootdir):
            raise KeyValidationError(f"Path ({k}) not valid. Must begin with {self.rootdir}")

    def __getitem__(self, k):
        self._validate_key(k)
        with open(self.rootdir + k, 'r' + self.mode) as fp:
            data = fp.read()
        return data

    def __setitem__(self, k, v):
        self._validate_key(k)
        with open(self.rootdir + k, 'w' + self.mode) as fp:
            fp.write(v)

    def __delitem__(self, k):
        self._validate_key(k)
        os.remove(k)

    def __iter__(self):
        return iter_filepaths_in_folder_recursively(self.rootdir)


class SimpleFileStore(Store):
    def __init__(self, rootdir, mode='t'):
        store = SimpleFilePersister(rootdir, mode)
        key_wrap = PrefixRelativization(_prefix=rootdir)
        super().__init__(store=store, _id_of_key=key_wrap._id_of_key, _key_of_id=key_wrap._key_of_id)


# LocalFileStore is a more flexible FileStore with more functionalities. Excluding to not detract from the essentials.
from py2store.persisters.local_files import PathFormatPersister, DFLT_OPEN_MODE


class LocalFileStore(Store):
    """ A store using local file persistence, with a relative path key interface """

    def __init__(self, path_format, mode=DFLT_OPEN_MODE, **open_kwargs):
        store = PathFormatPersister(path_format, mode=mode, **open_kwargs)
        key_wrap = PrefixRelativization(_prefix=store._prefix)
        super().__init__(store=store, _id_of_key=key_wrap._id_of_key, _key_of_id=key_wrap._key_of_id)

# NOTE: Moved DirStore to stores.local_store
#
# class DirReaderBase(Persister):
#     """ KV Reader whose keys (AND VALUES) are directory full paths of the subdirectories of _prefix rootdir.
#     Though this is a KV Reader, deletes are permitted, but only empty directories can be deleted.
#     """
#
#     def __init__(self, _prefix):
#         self._prefix = ensure_slash_suffix(_prefix)
#
#     def __contains__(self, k):
#         return k.startswith(self._prefix) and os.path.isdir(k)
#
#     def __iter__(self):
#         return filter(os.path.isdir, map(lambda x: os.path.join(self._prefix, x), os.listdir(self._prefix)))
#
#     def __getitem__(self, k):
#         if os.path.isdir(k):
#             return k
#         else:
#             raise NoSuchKeyError(f"No such key (perhaps it's not a directory, or was deleted?): {k}")
#
#     def __repr__(self):
#         return f"{self.__class__.__name__}('{self._prefix}')"
#
#     def __delitem__(self, k):
#         """ Remove empty directory k """
#         os.rmdir(k)
#
#     def __setitem__(self, k, v):
#         """ Remove empty directory k """
#         raise NotImplementedError("Setting a directory is not defined.")
#
#
# class DirStore(Store):
#     def __init__(self, rootdir):
#         rootdir = ensure_slash_suffix(rootdir)
#         self._prefix = rootdir
#         store = DirReaderBase(rootdir)
#         key_wrap = PrefixRelativization(_prefix=rootdir)
#         _obj_of_data = DirStore
#         _data_of_obj = lambda x: x._prefix
#         super().__init__(store=store,
#                          _id_of_key=key_wrap._id_of_key, _key_of_id=key_wrap._key_of_id,
#                          _obj_of_data=_obj_of_data, _data_of_obj=_data_of_obj)
#
#     def __repr__(self):
#         return f"{self.__class__.__name__}('{self._prefix}')"


########################################################################################################################
# S3

from botocore.exceptions import ClientError
from py2store.stores.s3_store import get_s3_resource
from py2store.stores.s3_store import DFLT_AWS_S3_ENDPOINT, DFLT_BOTO_CLIENT_VERIFY, DFLT_CONFIG
from functools import partial

encode_as_utf8 = partial(str, encoding='utf-8')

DFLT_S3_OBJ_OF_DATA = encode_as_utf8
from py2store.errors import NoSuchKeyError


class S3BucketPersister(Persister):
    def __init__(self, bucket_name: str, _s3_bucket, _prefix: str = ''):
        """
        S3 Bucket accessor.
        This class is meant to be subclassed, used with other mixins that actually add read and write methods.
        All S3BucketDacc does is create (or maintain) a bucket object, offer validation (is_valid)
        and assertion methods (assert_is_valid) methods to check that a key is prefixed by given _prefix, and
        more importantly, offers a hidden _id_of_key method that returns an object for a given key.

        Observe that the _s3_bucket constructor argument is a boto3 s3.Bucket, but offers other factories to make
        a S3BucketDacc instance.
        For example. if you only have access and secrete keys (and possibly endpoint url, config, etc.)
        then use the class method from_s3_resource_kwargs to construct.

        :param bucket_name: Bucket name (string)
        :param _s3_bucket: boto3 s3.Bucket object.
        :param _prefix: prefix that all accessed keys should have
        """
        self.bucket_name = bucket_name
        self._s3_bucket = _s3_bucket
        self._prefix = _prefix

    def __getitem__(self, k):
        try:  # TODO: Didn't manage to catch this exception for some reason. Make it work!
            return k.get()['Body'].read()
        except Exception as e:
            raise NoSuchKeyError("Key wasn't found: {}".format(k))
            # if hasattr(e, '__name__'):
            #     if e.__name__ == 'NoSuchKey':
            #         raise NoSuchKeyError("Key wasn't found: {}".format(k))
            # raise  # if you got so far

    def __setitem__(self, k, v):
        """
        Write data to s3 key.
        Method will check if key is valid before writing data to it,
        but will not check if data is already stored there.
        This means that any data previously stored at the key's location will be lost.
        :param k: s3 key
        :param v: data to write
        :return: None
        """
        # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
        k.put(Body=v)

    def __delitem__(self, k):
        """
        Delete data stored at key k.
        Method will check if key is valid before deleting its data.
        :param k:
        :return:
        """
        # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
        try:  # TODO: Didn't manage to catch this exception for some reason. Make it work!
            k.delete()
        except Exception as e:
            if hasattr(e, '__name__'):
                if e.__name__ == 'NoSuchKey':
                    raise NoSuchKeyError("Key wasn't found: {}".format(k))
            raise  # if you got so far

    def __iter__(self):
        return iter(self._s3_bucket.objects.filter(Prefix=self._prefix))

    def __contains__(self, k):
        """
        Check if key exists
        :param k: A key to search for
        :return: True if k exists, False if not
        """
        # TODO: s3_client.head_object(Bucket=dacc.bucket_name, Key=k) slightly more efficient but needs boto3.client
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
    def from_s3_resource_kwargs(cls,
                                bucket_name,
                                aws_access_key_id,
                                aws_secret_access_key,
                                _prefix: str = '',
                                endpoint_url=DFLT_AWS_S3_ENDPOINT,
                                verify=DFLT_BOTO_CLIENT_VERIFY,
                                config=DFLT_CONFIG):
        s3_resource = get_s3_resource(aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key,
                                      endpoint_url=endpoint_url,
                                      verify=verify,
                                      config=config)
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
        store = S3BucketPersister(bucket_name, _s3_bucket, _prefix)
        key_wrap = PrefixRelativization(_prefix=store._prefix)

        def _id_of_key(k):
            return store._s3_bucket.Object(key=key_wrap._id_of_key(k))

        def _key_of_id(_id):
            return key_wrap._key_of_id(_id.key)

        super().__init__(store=store,
                         _id_of_key=_id_of_key,
                         _key_of_id=_key_of_id,
                         _data_of_obj=_data_of_obj,
                         _obj_of_data=_obj_of_data
                         )

        # super().__init__(store=store, _id_of_key=key_wrap._id_of_key, _key_of_id=key_wrap._key_of_id)

    @classmethod
    def from_s3_resource_kwargs(cls,
                                bucket_name,
                                aws_access_key_id,
                                aws_secret_access_key,
                                _prefix: str = '',
                                _data_of_obj=lambda x: x,
                                _obj_of_data=DFLT_S3_OBJ_OF_DATA,
                                endpoint_url=DFLT_AWS_S3_ENDPOINT,
                                verify=DFLT_BOTO_CLIENT_VERIFY,
                                config=DFLT_CONFIG):
        s3_resource = get_s3_resource(aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key,
                                      endpoint_url=endpoint_url,
                                      verify=verify,
                                      config=config)
        return cls.from_s3_resource(bucket_name, s3_resource, _prefix=_prefix,
                                    _data_of_obj=_data_of_obj, _obj_of_data=_obj_of_data)

    @classmethod
    def from_s3_resource(cls,
                         bucket_name,
                         s3_resource,
                         _prefix='',
                         _data_of_obj=lambda x: x,
                         _obj_of_data=DFLT_S3_OBJ_OF_DATA,
                         ):
        s3_bucket = s3_resource.Bucket(bucket_name)
        return cls(bucket_name, s3_bucket, _prefix=_prefix,
                   _data_of_obj=_data_of_obj, _obj_of_data=_obj_of_data)
