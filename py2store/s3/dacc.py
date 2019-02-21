from py2store.base import AbstractKeys, AbstractObjReader, AbstractObjWriter, AbstractObjSource, AbstractObjStore
import boto3
from botocore.exceptions import ClientError
from py2store.util import lazyprop
from py2store.s3 import DFLT_AWS_S3_ENDPOINT, DFLT_BOTO_CLIENT_VERIFY, DFLT_CONFIG


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


def get_s3_bucket(name,
                  aws_access_key_id,
                  aws_secret_access_key,
                  endpoint_url=DFLT_AWS_S3_ENDPOINT,
                  verify=DFLT_BOTO_CLIENT_VERIFY,
                  config=DFLT_CONFIG):
    s3 = get_s3_resource(endpoint_url=endpoint_url,
                         aws_access_key_id=aws_access_key_id,
                         aws_secret_access_key=aws_secret_access_key,
                         verify=verify,
                         config=config)
    return s3.Bucket(name)


class S3BucketDacc(object):
    def __init__(self, bucket_name: str, _s3_bucket, _prefix: str = ''):
        """
        S3 Bucket accessor.
        This class is meant to be subclassed, used with other mixins that actually add read and write methods.
        All S3BucketDacc does is create (or maintain) a bucket object, offer validation (is_valid)
        and assertion methods (assert_is_valid) methods to check that a key is prefixed by given _prefix, and
        more importantly, offers a hidden _obj_of_key method that returns an object for a given key.

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

    @classmethod
    def from_s3_resource_kwargs(cls,
                                bucket_name,
                                aws_access_key_id,
                                aws_secret_access_key,
                                endpoint_url=DFLT_AWS_S3_ENDPOINT,
                                verify=DFLT_BOTO_CLIENT_VERIFY,
                                config=DFLT_CONFIG):
        s3_resource = get_s3_resource(aws_access_key_id=aws_access_key_id,
                                      aws_secret_access_key=aws_secret_access_key,
                                      endpoint_url=endpoint_url,
                                      verify=verify,
                                      config=config)
        return cls.from_s3_resource(bucket_name, s3_resource)

    @classmethod
    def from_s3_resource(cls,
                         bucket_name,
                         s3_resource):
        s3_bucket = s3_resource.Bucket(bucket_name)
        return cls(bucket_name, s3_bucket)

    def is_valid(self, k):
        return k.startswith(self._prefix)

    def assert_is_valid(self, k):
        assert self.is_valid(k), "key ({}) is not valid (prefix must be {})".format(k, self._prefix)

    def _obj_of_key(self, k):
        self.assert_is_valid(k)
        return self._s3_bucket.Object(key=k)


class S3BucketKeys(AbstractKeys, S3BucketDacc):
    """
    A S3BucketDacc collection.
    A collection is a iterable and sizable container.
    That is, this mixin adds iteration (__iter__), length (__len__), and containment (__contains__(k)) to S3BucketDacc.
    """
    def __iter__(self, prefix=None):
        if prefix is None:  # NOTE: I hesitate whether to give control over prefix at iteration time or not
            prefix = self._prefix
        return (x.key for x in self._s3_bucket.objects.filter(Prefix=prefix))

    def __contains__(self, k):
        """
        Check if key exists
        :param k: A key to search for
        :return: True if k exists, False if not
        """
        # TODO: s3_client.head_object(Bucket=dacc.bucket_name, Key=k) slightly more efficient but needs boto3.client
        try:
            self._obj_of_key(k).load()
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise
        else:
            return True

    # def __len__(self, k):  # TODO: Is there a s3 specific more efficient way of doing __len__?
    #     pass


class S3BucketReader(AbstractObjReader, S3BucketDacc):
    """ Adds a __getitem__ to S3BucketDacc, which returns a bucket's object binary data for a key."""
    def __getitem__(self, k):
        return self._obj_of_key(k).get()['Body'].read()


class S3BucketSource(AbstractObjSource, S3BucketKeys, S3BucketReader):
    """
    A S3BucketDacc mapping (i.e. a collection (iterable, sizable container) that has a reader (__getitem__),
    and mapping mixin methods such as get, keys, items, values, __eq__ and __ne__.
    """
    pass


class S3BucketWriter(AbstractObjWriter, S3BucketDacc):
    """ A S3BucketDacc that can write to s3 """
    def __setitem__(self, k, v):
        """
        Write data to s3 key.
        :param k: s3 key
        :param v: data to write
        :return: None
        """
        # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
        self._obj_of_key(k).put(Body=v)

    def __delitem__(self, k):
        # TODO: Faster to ignore s3 response, but perhaps better to get it, possibly cache it, and possibly handle it
        self._obj_of_key(k).delete()


class S3BucketStore(AbstractObjStore, S3BucketSource, S3BucketWriter):
    """
    A S3BucketDacc MutableMapping.
    That is, a S3BucketDacc that can read and write, as well as iterate
    """
    pass
