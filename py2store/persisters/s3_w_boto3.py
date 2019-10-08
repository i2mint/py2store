from functools import partial

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from botocore.client import Config
    from botocore.exceptions import ClientError
    import boto3

from py2store.base import Persister


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


# TODO: I wanted boto3.resources.factory.s3.ObjectSummary but couldn't find it
from boto3.resources.base import ServiceResource


def isdir(obj_summary: ServiceResource):
    return obj_summary.size == 0 and obj_summary.key.endswith


def isfile(obj_summary: ServiceResource):
    return not isdir(obj_summary)


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
        return filter(isfile, self._s3_bucket.objects.filter(Prefix=self._prefix))

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
    def from_s3_resource_kwargs(cls, bucket_name, _prefix: str = '', resource_kwargs=None):
        s3_resource = get_s3_resource(**(resource_kwargs or {}))
        return cls.from_s3_resource(bucket_name, s3_resource, _prefix=_prefix)

    @classmethod
    def from_s3_resource(cls,
                         bucket_name,
                         s3_resource,
                         _prefix=''
                         ):
        s3_bucket = s3_resource.Bucket(bucket_name)
        return cls(bucket_name, s3_bucket, _prefix=_prefix)


# Experimental functions to be used to enhance methods for file system stores
# See File
try:
    from boto3.resources.base import ServiceResource


    def isdir(obj_summary: ServiceResource):
        return obj_summary.size == 0 and obj_summary.key.endswith

except:
    pass
