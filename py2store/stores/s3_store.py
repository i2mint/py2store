import pickle
from py2store.base import Store
from py2store.util import ModuleNotFoundErrorNiceMessage
from py2store.persisters.s3_w_boto3 import S3BucketPersister
from py2store.key_mappers.paths import mk_relative_path_store

with ModuleNotFoundErrorNiceMessage():
    from botocore.client import Config

DFLT_AWS_S3_ENDPOINT = "https://s3.amazonaws.com"
DFLT_BOTO_CLIENT_VERIFY = None
DFLT_SIGNATURE_VERSION = 's3v4'
DFLT_CONFIG = Config(signature_version=DFLT_SIGNATURE_VERSION)


class S3AbsPathBinaryStore(Store):
    # @wraps(S3BucketPersister.from_s3_resource_kwargs)
    def __init__(self, bucket_name, _prefix: str = '', resource_kwargs=None):
        persister = S3BucketPersister.from_s3_resource_kwargs(bucket_name, _prefix, resource_kwargs)
        super().__init__(persister)
        self._prefix = self.store._prefix

    def _id_of_key(self, k):
        return self.store._s3_bucket.Object(key=k)

    def _key_of_id(self, _id):
        return _id.key


S3BinaryStore = mk_relative_path_store(S3AbsPathBinaryStore, 'S3BinaryStore')


class S3TextStore(S3BinaryStore):
    def _obj_of_data(self, data):
        return data.decode()


S3StringStore = S3TextStore


class S3PickleStore(S3BinaryStore):

    def _obj_of_data(self, data):
        return pickle.loads(data)

    def _data_of_obj(self, obj):
        return pickle.dumps(obj)

# def get_s3_resource(aws_access_key_id,
#                     aws_secret_access_key,
#                     endpoint_url=DFLT_AWS_S3_ENDPOINT,
#                     verify=DFLT_BOTO_CLIENT_VERIFY,
#                     config=DFLT_CONFIG):
#     """
#     Get boto3 s3 resource.
#     :param aws_access_key_id:
#     :param aws_secret_access_key:
#     :param endpoint_url:
#     :param verify:
#     :param signature_version:
#     :return:
#     """
#     return boto3.resource('s3',
#                           endpoint_url=endpoint_url,
#                           aws_access_key_id=aws_access_key_id,
#                           aws_secret_access_key=aws_secret_access_key,
#                           verify=verify,
#                           config=config)
#
#
# def get_s3_bucket(name,
#                   aws_access_key_id,
#                   aws_secret_access_key,
#                   endpoint_url=DFLT_AWS_S3_ENDPOINT,
#                   verify=DFLT_BOTO_CLIENT_VERIFY,
#                   config=DFLT_CONFIG):
#     s3 = get_s3_resource(endpoint_url=endpoint_url,
#                          aws_access_key_id=aws_access_key_id,
#                          aws_secret_access_key=aws_secret_access_key,
#                          verify=verify,
#                          config=config)
#     return s3.Bucket(name)


# class S3BucketCollection(IterBasedSizedMixin):
#     """
#     A S3BucketDacc collection.
#     A collection is a iterable and sizable container.
#     That is, this mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)) to S3BucketDacc.
#
#     Note: Subclasses IterBasedSizedMixin for the sole purpose of reusing it's __len__ method before any KV wrapping
#     """
#
#     def __iter__(self):
#         return iter(self._s3_bucket.objects.filter(Prefix=self._prefix))
#
#     def __contains__(self, k):
#         """
#         Check if key exists
#         :param k: A key to search for
#         :return: True if k exists, False if not
#         """
#         # TODO: s3_client.head_object(Bucket=dacc.bucket_name, Key=k) slightly more efficient but needs boto3.client
#         try:
#             self._id_of_key(k).load()
#             return True  # if all went well
#         except ClientError as e:
#             if e.response['Error']['Code'] == "404":
#                 # The object does not exist.
#                 return False
#             else:
#                 # Something else has gone wrong.
#                 raise
#
#     def _id_of_key(self, k):
#         return self._s3_bucket.Object(key=k)
#
#     def _key_of_id(self, _id):
#         return _id.key
#
#
# class S3BucketReaderMixin:
#     """ Mixin to add read functionality to a S3BucketDacc."""
#
#     def __getitem__(self, k):
#         try:  # TODO: Didn't manage to catch this exception for some reason. Make it work!
#             return k.get()['Body'].read()
#         except Exception as e:
#             if hasattr(e, '__name__'):
#                 if e.__name__ == 'NoSuchKey':
#                     raise NoSuchKeyError("Key wasn't found: {}".format(k))
#             raise  # if you got so far
#
#
# class S3BucketWriterMixin:
#     """ A mixin to add write and delete functionality """
#
#     def __setitem__(self, k, v):
#         """
#         Write data to s3 key.
#         Method will check if key is valid before writing data to it,
#         but will not check if data is already stored there.
#         This means that any data previously stored at the key's location will be lost.
#         :param k: s3 key
#         :param v: data to write
#         :return: None
#         """
#         # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
#         k.put(Body=v)
#
#
# class S3BucketDeleterMixin:
#     def __delitem__(self, k):
#         """
#         Delete data stored at key k.
#         Method will check if key is valid before deleting its data.
#         :param k:
#         :return:
#         """
#         # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
#         try:  # TODO: Didn't manage to catch this exception for some reason. Make it work!
#             k.delete()
#         except Exception as e:
#             if hasattr(e, '__name__'):
#                 if e.__name__ == 'NoSuchKey':
#                     raise NoSuchKeyError("Key wasn't found: {}".format(k))
#             raise  # if you got so far
#
#
# class S3BucketRWD(S3BucketReaderMixin, S3BucketWriterMixin, S3BucketDeleterMixin):
#     def __init__(self, bucket_name: str, _s3_bucket, _prefix: str = ''):
#         """
#         S3 Bucket accessor.
#         This class is meant to be subclassed, used with other mixins that actually add read and write methods.
#         All S3BucketDacc does is create (or maintain) a bucket object, offer validation (is_valid)
#         and assertion methods (assert_is_valid) methods to check that a key is prefixed by given _prefix, and
#         more importantly, offers a hidden _id_of_key method that returns an object for a given key.
#
#         Observe that the _s3_bucket constructor argument is a boto3 s3.Bucket, but offers other factories to make
#         a S3BucketDacc instance.
#         For example. if you only have access and secrete keys (and possibly endpoint url, config, etc.)
#         then use the class method from_s3_resource_kwargs to construct.
#
#         :param bucket_name: Bucket name (string)
#         :param _s3_bucket: boto3 s3.Bucket object.
#         :param _prefix: prefix that all accessed keys should have
#         """
#         self.bucket_name = bucket_name
#         self._s3_bucket = _s3_bucket
#         self._prefix = _prefix
#
#     @classmethod
#     def from_s3_resource_kwargs(cls,
#                                 bucket_name,
#                                 aws_access_key_id,
#                                 aws_secret_access_key,
#                                 _prefix: str = '',
#                                 endpoint_url=DFLT_AWS_S3_ENDPOINT,
#                                 verify=DFLT_BOTO_CLIENT_VERIFY,
#                                 config=DFLT_CONFIG):
#         s3_resource = get_s3_resource(aws_access_key_id=aws_access_key_id,
#                                       aws_secret_access_key=aws_secret_access_key,
#                                       endpoint_url=endpoint_url,
#                                       verify=verify,
#                                       config=config)
#         return cls.from_s3_resource(bucket_name, s3_resource, _prefix=_prefix)
#
#     @classmethod
#     def from_s3_resource(cls,
#                          bucket_name,
#                          s3_resource,
#                          _prefix=''):
#         s3_bucket = s3_resource.Bucket(bucket_name)
#         return cls(bucket_name, s3_bucket, _prefix=_prefix)

# StoreInterface, S3BucketCollection, S3BucketRWD, StoreMutableMapping
# from py2store.base import StoreMutableMapping


# class Store(StoreBaseMixin, S3BucketRWD, PrefixRelativizationMixin, S3BucketCollection, IdentityKvWrapMixin):
#     pass

# from py2store.base import StoreBase, Store

# class S3BucketStoreBase(S3BucketCollection, StoreBaseMixin, StringKvWrap, StoreBase):
#     pass
#
#
# class S3BucketStoreNoOverwrites(OverWritesNotAllowedMixin, S3BucketStore):
#     pass


#
# class RelativePathFormatStore(PrefixRelativizationMixin, PathFormatStore):
#     pass
#
#
# from py2store.core import PrefixRelativizationMixin
#
#
#
# # StoreInterface, FilepathFormatKeys, LocalFileRWD, StoreMutableMapping
# # class S3BucketCollection(PrefixRelativizationMixin, S3BucketDacc, S3BucketCollection):
# #     pass
#
#
# class S3BucketReader(PrefixRelativizationMixin, S3BucketDacc, S3BucketReaderMixin):
#     """ Adds a __getitem__ to S3BucketDacc, which returns a bucket's object binary data for a key."""
#     pass
#
#
# class S3BucketSource(PrefixRelativizationMixin, AbstractObjSource, S3BucketCollection, S3BucketReaderMixin, S3BucketDacc):
#     """
#     A S3BucketDacc mapping (i.e. a collection (iterable, sizable container) that has a reader (__getitem__),
#     and mapping mixin methods such as get, keys, items, values, __eq__ and __ne__.
#     """
#     pass
#
#
# class S3BucketWriter(PrefixRelativizationMixin, S3BucketDacc, S3BucketWriterMixin):
#     """ A S3BucketDacc that can write to s3 and delete keys (and data) """
#     pass
#
#
# class S3BucketWriterNoOverwrites(OverWritesNotAllowedMixin, S3BucketWriter):
#     """
#     Exactly like S3BucketWriter, but where writes to an already existing key are protected.
#     If a key already exists, __setitem__ will raise a OverWritesNotAllowedError
#     """
#     pass
#
#
#
#
# class S3BucketStore(PrefixRelativizationMixin, S3BucketDacc, AbstractObjStore, S3BucketCollection,
#                     S3BucketReaderMixin, S3BucketWriterMixin):
#     """
#     A S3BucketDacc MutableMapping.
#     That is, a S3BucketDacc that can read and write, as well as iterate
#     """
#     pass
#
#
# class S3BucketStoreNoOverwrites(OverWritesNotAllowedMixin, S3BucketStore):
#     """
#     A S3BucketDacc MutableMapping.
#     That is, a S3BucketDacc that can read and write, as well as iterate
#     """
#     pass
