from functools import partial
from typing import Iterable, NewType
from py2store.util import ModuleNotFoundErrorNiceMessage, lazyprop

with ModuleNotFoundErrorNiceMessage():
    from botocore.client import Config, BaseClient
    from botocore.exceptions import ClientError
    import boto3
    from boto3.resources.base import ServiceResource

    S3BucketType = NewType('S3BucketType', ServiceResource)  # TODO: hack -- find how to import an actual Bucket type

from py2store.base import KvReader, KvPersister, Collection


class S3KeyError(KeyError): ...


class NoSuchKeyError(S3KeyError): ...


class KeyNotValidError(S3KeyError): ...


class GetItemForKeyError(S3KeyError): ...


encode_as_utf8 = partial(str, encoding='utf-8')

# TODO: Make capability of overriding defaults externally.
DFLT_S3_OBJ_OF_DATA = encode_as_utf8
DFLT_AWS_S3_ENDPOINT = "https://s3.amazonaws.com"
DFLT_BOTO_CLIENT_VERIFY = None
DFLT_SIGNATURE_VERSION = 's3v4'
DFLT_CONFIG = Config(signature_version=DFLT_SIGNATURE_VERSION)


def get_s3_client(aws_access_key_id,
                  aws_secret_access_key,
                  endpoint_url=DFLT_AWS_S3_ENDPOINT,
                  verify=DFLT_BOTO_CLIENT_VERIFY,
                  config=DFLT_CONFIG):
    return boto3.client('s3',
                        endpoint_url=endpoint_url,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key,
                        verify=verify,
                        config=config)


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
from dataclasses import dataclass


@dataclass
class S3BucketBaseReader(KvReader):
    """Base bucket reader. Keys are strings, values are http responses (dicts).

    To get the actual contents from the response `v` you can do `v['Body'].read()`, or more sophisticated-ly:
    ```
    if v['ResponseMetadata']['HTTPStatusCode'] == 200:
        return v['Body'].read()
    else:
        raise RuntimeError(f"HttpError (code {v['ResponseMetadata']['HTTPStatusCode']})")
    ```

    But know that `body = v['Body']` is a `botocore.response.StreamingBody` instance, and as such, you have not
    only the `body.read(amt=None)` but also
    - `body.iter_chunks(chunk_size=1024)` that may be useful for large binary data, or
    - `body.iter_lines(chunk_size=1024)` that may be useful for large text data.

    S3BucketBaseReader is really meant to be wrapped and/or subclassed into interfaces that do that for you.

    Example use:
    ```
    resource_kwargs = get_configs()  # get (at least) aws_access_key_id and aws_secret_access_key
    r = S3BucketBaseReader(S3BucketBaseReader.mk_client(**resources_kwargs), bucket='bucket_name', prefix='my_stuff/')
    list(r)  # will list file and folder names
    r['my_stuff/music/']  # will give you another S3BucketBaseReader for that "subfolder"
    r['my_stuff/music/with_meaning.mp3']  # will give you the response object for the contents of the file
    ```
    """
    client: BaseClient
    bucket: str
    prefix: str = ''
    with_files: bool = True
    with_directories: bool = True

    def __post_init__(self):
        self._source = self.client
        self._filt = dict(Prefix=self.prefix, Delimiter='/')

    def is_valid_key(self, k):
        return isinstance(k, str) and k.startswith(self.prefix)

    def validate_key(self, k):
        if not self.is_valid_key(k):
            if not isinstance(k, str):
                raise KeyNotValidError(f"Key should be a string. Your key is: {k}")
            elif not k.startswith(self.prefix):
                raise KeyNotValidError(f"Prefix of key should be '{self.prefix}'. Your key is: {k}")
            else:
                raise KeyNotValidError(f"Not a valid key: {k}")

    def __getitem__(self, k: str):
        self.validate_key(k)
        if not k.endswith('/'):
            try:
                return self._source.get_object(Bucket=self.bucket, Key=k)
            except Exception as e:
                raise GetItemForKeyError(f"Problem retrieving value for key: {k}")
        else:  # assume it's a "directory"
            return self.__class__(client=self._source,
                                  bucket=self.bucket,
                                  prefix=k,
                                  with_files=self.with_files,
                                  with_directories=self.with_directories)

    def object_list_pages(self):
        # TODO: compare list_objects to list_object_v2. Should we switch?
        yield from self._source.get_paginator('list_objects').paginate(Bucket=self.bucket, **self._filt)

    def __iter__(self):
        for resp in self.object_list_pages():
            if self.with_files and 'Contents' in resp:
                for d in resp['Contents']:
                    yield d['Key']
            if self.with_directories and 'CommonPrefixes' in resp:
                for d in resp['CommonPrefixes']:
                    yield d['Prefix']

    def head_object(self, k):
        self.validate_key(k)
        return self._source.head_object(Bucket=self.bucket, Key=k)

    def __contains__(self, k):
        try:
            self.head_object(k)
            return True  # if all went well
        except KeyNotValidError as e:
            raise
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise

    @wraps(get_s3_client)
    @staticmethod
    def mk_client(**resource_kwargs):
        return get_s3_client(**resource_kwargs)
    #
    # @classmethod
    # def from_s3_resource_kwargs(cls, bucket_name, filt=None, resource_kwargs=None):
    #     s3_resource = get_s3_resource(**(resource_kwargs or {}))
    #     return cls.from_s3_resource(bucket_name, s3_resource, filt=filt)
    #
    # @classmethod
    # def from_s3_resource(cls,
    #                      bucket_name,
    #                      s3_resource,
    #                      filt=None
    #                      ):
    #     s3_bucket = s3_resource.Bucket(bucket_name)
    #     return cls(s3_bucket, filt=filt)
    #
    # @classmethod
    # def from_s3_resource_kwargs_and_prefix(cls, bucket_name, _prefix: str = '', resource_kwargs=None):
    #     return cls.from_s3_resource_kwargs(bucket_name, dict(Prefix=_prefix), resource_kwargs)
    #
    # @classmethod
    # def from_s3_resource_and_prefix(cls,
    #                                 bucket_name,
    #                                 s3_resource,
    #                                 _prefix=''
    #                                 ):
    #     return cls.from_s3_resource(bucket_name, s3_resource, filt=dict(Prefix=_prefix))


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
