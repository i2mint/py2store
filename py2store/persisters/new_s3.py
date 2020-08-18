from functools import partial
from typing import Iterable, NewType
from py2store.util import ModuleNotFoundErrorNiceMessage, lazyprop

with ModuleNotFoundErrorNiceMessage():
    from botocore.client import Config
    from botocore.exceptions import ClientError
    import boto3
    from boto3.resources.base import ServiceResource

    S3BucketType = NewType('S3BucketType', ServiceResource)  # TODO: hack -- find how to import an actual Bucket type

from py2store.base import KvReader, KvPersister, Collection


class NoSuchKeyError(KeyError):
    pass


encode_as_utf8 = partial(str, encoding='utf-8')

# TODO: Make capability of overriding defaults externally.
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


def _s3_resource_initializer(self, aws_access_key_id,
                             aws_secret_access_key,
                             endpoint_url=DFLT_AWS_S3_ENDPOINT,
                             verify=DFLT_BOTO_CLIENT_VERIFY,
                             config=DFLT_CONFIG):
    self._source = get_s3_resource(endpoint_url=endpoint_url,
                                   aws_access_key_id=aws_access_key_id,
                                   aws_secret_access_key=aws_secret_access_key,
                                   verify=verify,
                                   config=config)


from py2store.trans import cached_keys


@cached_keys(keys_cache=list)
class S3ResourceCollection(Collection):
    _source = None  # to tell lint about it (TODO: Find less hacky way to talk to lint)
    __init__ = _s3_resource_initializer

    def __iter__(self) -> Iterable[S3BucketType]:
        return self._source.buckets.all()


from functools import wraps


def extract_key(d):
    return d['Key']


def extract_prefix(d):
    return d['Prefix']


def get_file_contents_for_key(bucket, k: str):
    try:
        b = BytesIO()
        bucket.download_fileobj(k, b)
        b.seek(0)
        return b.read()
    except Exception as e:
        raise NoSuchKeyError("Key wasn't found: {}".format(k))


# def get_dir_key(bucket, k: str):
#   raise NotImplemented("not yet")

from io import BytesIO


class S3BucketBaseReader(KvReader):
    def __init__(self, s3_bucket,
                 filt=None,
                 with_files=True,
                 with_directories=True):
        self._source = s3_bucket
        self._client = s3_bucket.meta.client
        self.bucket_name = s3_bucket.name
        self.filt = filt or {}
        self._prefix = self.filt.get('Prefix', '')
        self.with_files = with_files
        self.with_directories = with_directories

    def __getitem__(self, k: str):
        if not k.endswith('/'):
            try:
                b = BytesIO()
                self._source.download_fileobj(k, b)
                b.seek(0)
                return b.read()
            except Exception as e:
                raise NoSuchKeyError("Key wasn't found: {}".format(k))
        else:  # assume it's a "directory"
            filt = self.filt.copy()
            filt.update(Prefix=k)
            return self.__class__(s3_bucket=self._source,
                                  filt=filt,
                                  with_files=self.with_files,
                                  with_directories=self.with_directories)

    def object_list_pages(self):
        yield from self._client.get_paginator('list_objects').paginate(Bucket=self.bucket_name, **self.filt)

    def __iter__(self):
        for resp in self.object_list_pages():
            if self.with_files and 'Contents' in resp:
                for d in resp['Contents']:
                    yield d['Key']
            if self.with_directories and 'CommonPrefixes' in resp:
                for d in resp['CommonPrefixes']:
                    yield d['Prefix']

    # TODO: Not sufficient in the presence of filt. Need to validate key against more of filt's fields.
    def is_valid_key(self, k):
        return k.startswith(self._prefix)

    def __contains__(self, k):
        if not self.is_valid_key(k):
            return False
        try:
            k.load()  # TODO: Find another way that can check keys existence without using so much bandwith!
            return True  # if all went well
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise

    @wraps(get_s3_bucket)
    @staticmethod
    def mk_bucket(bucket_name, **resource_kwargs):
        return get_s3_bucket(bucket_name, **resource_kwargs)

    @classmethod
    def from_s3_resource_kwargs(cls, bucket_name, filt=None, resource_kwargs=None):
        s3_resource = get_s3_resource(**(resource_kwargs or {}))
        return cls.from_s3_resource(bucket_name, s3_resource, filt=filt)

    @classmethod
    def from_s3_resource(cls,
                         bucket_name,
                         s3_resource,
                         filt=None
                         ):
        s3_bucket = s3_resource.Bucket(bucket_name)
        return cls(s3_bucket, filt=filt)

    @classmethod
    def from_s3_resource_kwargs_and_prefix(cls, bucket_name, _prefix: str = '', resource_kwargs=None):
        return cls.from_s3_resource_kwargs(bucket_name, dict(Prefix=_prefix), resource_kwargs)

    @classmethod
    def from_s3_resource_and_prefix(cls,
                                    bucket_name,
                                    s3_resource,
                                    _prefix=''
                                    ):
        return cls.from_s3_resource(bucket_name, s3_resource, filt=dict(Prefix=_prefix))


# TODO: Everything below needs to be done under the form of the new base
# Assigning the alias "S3BucketReader" to be "S3BucketBaseReader" just to make the module load.
S3BucketReader = S3BucketBaseReader


class S3BucketRW(S3BucketReader, KvPersister):
    def __setitem__(self, k, v):
        pass
        # TODO: Use self._source.upload_fileobj instead
        # return k.put(Body=v)

    def __delitem__(self, k):
        pass
        # TODO: Use self._source.delete_objects instead
        # try:
        #     return k.delete()
        # except Exception as e:
        #     if hasattr(e, '__name__'):
        #         if e.__name__ == 'NoSuchKey':
        #             raise NoSuchKeyError("Key wasn't found: {}".format(k))
        #     raise  # if you got so far


# TODO: Make some stores that have more convenient interfaces
#   (e.g. see existing py2store.store.s3_store and rewrite versions of those stores that use the
#   present new way)

# Pattern: reader from collection + mapping maker.
# TODO: Make a special factory out of the pattern
class S3ResourceReader(S3ResourceCollection):
    item_cls = S3BucketReader

    @wraps(S3ResourceCollection.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._source = {b.name: b for b in super().__iter__()}

    def __iter__(self) -> Iterable[S3BucketType]:
        yield from self._source

    def __getitem__(self, k):
        return self.item_cls(self._source[k])
