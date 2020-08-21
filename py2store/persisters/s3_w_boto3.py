from functools import partial
from typing import Iterable, NewType
from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from botocore.client import Config
    from botocore.exceptions import ClientError
    import boto3
    from boto3.resources.base import ServiceResource

    S3BucketType = NewType(
        "S3BucketType", ServiceResource
    )  # TODO: hack -- find how to import an actual Bucket type

from py2store.base import KvReader, KvPersister, Collection


class NoSuchKeyError(KeyError):
    pass


encode_as_utf8 = partial(str, encoding="utf-8")

DFLT_S3_OBJ_OF_DATA = encode_as_utf8
DFLT_AWS_S3_ENDPOINT = "https://s3.amazonaws.com"
DFLT_BOTO_CLIENT_VERIFY = None
DFLT_SIGNATURE_VERSION = "s3v4"
DFLT_CONFIG = Config(signature_version=DFLT_SIGNATURE_VERSION)


def get_s3_resource(
        aws_access_key_id,
        aws_secret_access_key,
        endpoint_url=DFLT_AWS_S3_ENDPOINT,
        verify=DFLT_BOTO_CLIENT_VERIFY,
        config=DFLT_CONFIG,
):
    """
    Get boto3 s3 resource.
    :param aws_access_key_id:
    :param aws_secret_access_key:
    :param endpoint_url:
    :param verify:
    :param signature_version:
    :return:
    """
    return boto3.resource(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        verify=verify,
        config=config,
    )


def get_s3_bucket(
        name,
        aws_access_key_id,
        aws_secret_access_key,
        endpoint_url=DFLT_AWS_S3_ENDPOINT,
        verify=DFLT_BOTO_CLIENT_VERIFY,
        config=DFLT_CONFIG,
):
    s3 = get_s3_resource(
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        verify=verify,
        config=config,
    )
    return s3.Bucket(name)


# TODO: I wanted boto3.resources.factory.s3.ObjectSummary but couldn't find it
from boto3.resources.base import ServiceResource


def isdir(obj_summary: ServiceResource):
    return obj_summary.size == 0 and obj_summary.key.endswith


def isfile(obj_summary: ServiceResource):
    return not isdir(obj_summary)


def _resource_initializer(
        self,
        aws_access_key_id,
        aws_secret_access_key,
        endpoint_url=DFLT_AWS_S3_ENDPOINT,
        verify=DFLT_BOTO_CLIENT_VERIFY,
        config=DFLT_CONFIG,
):
    self._source = get_s3_resource(
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        verify=verify,
        config=config,
    )


from py2store.trans import cached_keys


@cached_keys(keys_cache=list)
class S3ResourceCollection(Collection):
    _source = None  # to tell lint about it (TODO: Find less hacky way to talk to lint)
    __init__ = _resource_initializer

    def __iter__(self) -> Iterable[S3BucketType]:
        return self._source.buckets.all()


from functools import wraps


# Pattern: reader from collection + mapping maker.
# TODO: Make a special factory out of the pattern
class S3ResourceReader(S3ResourceCollection):
    @wraps(S3ResourceCollection.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._source = {b.name: b for b in super().__iter__()}

    def __iter__(self) -> Iterable[S3BucketType]:
        yield from self._source

    def __getitem__(self, k):
        return S3BucketReader(self._source[k])


class S3BucketReader(KvReader):
    def __init__(self, s3_bucket, filt=None):
        self._source = s3_bucket
        self.bucket_name = s3_bucket.name
        self.filt = filt or {}

    def __getitem__(self, k):
        try:
            return k.get()["Body"].read()
        except Exception as e:
            raise NoSuchKeyError("Key wasn't found: {}".format(k))

    def __iter__(self):
        yield from self._source.objects.filter(**self.filt)
        # return filter(isfile, self._source.objects.filter(**self.filt))

    def __contains__(self, k):
        try:
            k.load()
            return True  # if all went well
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise

    @classmethod
    def from_s3_resource_kwargs(
            cls, bucket_name, filt=None, resource_kwargs=None
    ):
        s3_resource = get_s3_resource(**(resource_kwargs or {}))
        return cls.from_s3_resource(bucket_name, s3_resource, filt=filt)

    @classmethod
    def from_s3_resource(cls, bucket_name, s3_resource, filt=None):
        s3_bucket = s3_resource.Bucket(bucket_name)
        return cls(s3_bucket, filt=filt)

    @classmethod
    def from_s3_resource_kwargs_and_prefix(
            cls, bucket_name, _prefix: str = "", resource_kwargs=None
    ):
        return cls.from_s3_resource_kwargs(
            bucket_name, dict(Prefix=_prefix), resource_kwargs
        )

    @classmethod
    def from_s3_resource_and_prefix(cls, bucket_name, s3_resource, _prefix=""):
        return cls.from_s3_resource(
            bucket_name, s3_resource, filt=dict(Prefix=_prefix)
        )


class S3BucketRW(S3BucketReader, KvPersister):
    def __setitem__(self, k, v):
        return k.put(Body=v)

    def __delitem__(self, k):
        try:
            return k.delete()
        except Exception as e:
            if hasattr(e, "__name__"):
                if e.__name__ == "NoSuchKey":
                    raise NoSuchKeyError("Key wasn't found: {}".format(k))
            raise  # if you got so far


# Planning on deprecating this one in favor of S3BucketRW
class S3BucketPersister(KvPersister):
    # Planning on deprecating this one in favor of S3BucketRW
    def __init__(self, bucket_name: str, _s3_bucket, _prefix: str = ""):
        self.bucket_name = bucket_name
        self._s3_bucket = _s3_bucket  # kept for back-compatibility and reference (so we know what source is)
        self._source = _s3_bucket  # to be the new consistent source
        self._prefix = _prefix

    def __getitem__(self, k):
        try:
            return k.get()["Body"].read()
        except Exception as e:
            raise NoSuchKeyError("Key wasn't found: {}".format(k))

    def __setitem__(self, k, v):
        k.put(Body=v)

    def __delitem__(self, k):
        try:
            k.delete()
        except Exception as e:
            if hasattr(e, "__name__"):
                if e.__name__ == "NoSuchKey":
                    raise NoSuchKeyError("Key wasn't found: {}".format(k))
            raise  # if you got so far

    def __iter__(self):
        return filter(isfile, self._source.objects.filter(Prefix=self._prefix))

    def __contains__(self, k):
        try:
            k.load()
            return True  # if all went well
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise

    @classmethod
    def from_s3_resource_kwargs(
            cls, bucket_name, _prefix: str = "", resource_kwargs=None
    ):
        s3_resource = get_s3_resource(**(resource_kwargs or {}))
        return cls.from_s3_resource(bucket_name, s3_resource, _prefix=_prefix)

    @classmethod
    def from_s3_resource(cls, bucket_name, s3_resource, _prefix=""):
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
