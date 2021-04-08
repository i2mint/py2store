from functools import partial, wraps
from typing import Iterable, NewType, Union, Callable, Any
from collections.abc import Mapping
from dataclasses import dataclass
from warnings import warn

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from botocore.client import Config, BaseClient
    from botocore.exceptions import ClientError
    from botocore.response import StreamingBody
    from boto3 import client
    from boto3.resources.base import ServiceResource

    S3BucketType = NewType(
        "S3BucketType", ServiceResource
    )  # TODO: hack -- find how to import an actual Bucket type

from py2store.base import KvReader, KvPersister, Collection


class S3KeyError(KeyError):
    ...


class NoSuchKeyError(S3KeyError):
    ...


class KeyNotValidError(S3KeyError):
    ...


class GetItemForKeyError(S3KeyError):
    ...


class S3HttpError(RuntimeError):
    ...


class S3Not200StatusCodeError(S3HttpError):
    ...


def raise_on_error(d: dict):
    raise


def return_none_on_error(d: dict):
    return None


def return_empty_tuple_on_error(d: dict):
    return ()


OnErrorType = Union[Callable[[dict], Any], str]


def path_get(
        mapping,
        path,
        on_error: OnErrorType = raise_on_error,
        caught_errors=(KeyError,),
):
    result = mapping
    for k in path:
        try:
            result = result[k]
        except caught_errors as error:
            if callable(on_error):
                return on_error(
                    dict(
                        mapping=mapping,
                        path=path,
                        result=result,
                        k=k,
                        error=error,
                    )
                )
            elif isinstance(on_error, str):
                try:
                    raise error.__class__(
                        on_error
                    )  # use on_error as a message, raising the same error class
                except Exception:
                    raise S3KeyError(
                        on_error
                    )  # if that doesn't work, just raise a S3KeyError
            else:
                raise ValueError(
                    f"on_error should be a callable (input is a dict) or a string. "
                    f"Was: {on_error}"
                )
    return result


encode_as_utf8 = partial(str, encoding="utf-8")

# TODO: Make capability of overriding defaults externally.
DFLT_S3_OBJ_OF_DATA = encode_as_utf8
DFLT_AWS_S3_ENDPOINT = "https://s3.amazonaws.com"
DFLT_BOTO_CLIENT_VERIFY = None
DFLT_SIGNATURE_VERSION = "s3v4"
DFLT_CONFIG = Config(signature_version=DFLT_SIGNATURE_VERSION)


def get_s3_client(
        aws_access_key_id,
        aws_secret_access_key,
        endpoint_url=DFLT_AWS_S3_ENDPOINT,
        verify=DFLT_BOTO_CLIENT_VERIFY,
        config=DFLT_CONFIG,
):
    return client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        verify=verify,
        config=config,
    )


def ensure_client(candidate_client):
    """Ensure input is a BaseClient (either kwargs to make one, or already a BaseClient instance."""
    if isinstance(candidate_client, Mapping):
        return get_s3_client(
            **candidate_client
        )  # consider candidate_client as kwargs to make one
    # TODO: Be more precise (botocore.client.S3 doesn't exist, so took BaseClient):
    assert isinstance(candidate_client, BaseClient)
    return candidate_client


def isdir_key(key: str):
    return key.endswith("/")


def isfile_key(key: str):
    return not key.endswith("/")


# TODO: Consider pros/cons of subclassing or delegating dict.
# TODO: Consider reducing visual noise with staticmethod|partial composition
# Pattern: Named nested access (glom etc.)
class Resp:
    @staticmethod
    def status_code(d, on_error: OnErrorType = raise_on_error):
        return path_get(d, ["ResponseMetadata", "HTTPStatusCode"], on_error)

    @staticmethod
    def contents(d, on_error: OnErrorType = return_empty_tuple_on_error):
        return path_get(d, ["Contents"], on_error)

    @staticmethod
    def key(d, on_error: OnErrorType = raise_on_error):
        return path_get(d, ["Key"], on_error)

    @staticmethod
    def common_prefixes(
            d, on_error: OnErrorType = return_empty_tuple_on_error
    ):
        return path_get(d, ["CommonPrefixes"], on_error)

    @staticmethod
    def prefix(d, on_error: OnErrorType = raise_on_error):
        return path_get(d, ["Prefix"], on_error)

    @staticmethod
    def buckets(d, on_error: OnErrorType = return_empty_tuple_on_error):
        return path_get(d, ["Buckets"], on_error)

    @staticmethod
    def body(d, on_error: OnErrorType = return_none_on_error):
        return path_get(d, ["Body"], on_error)

    @staticmethod
    def ascertain_status_code(
            d,
            status_code=200,
            raise_error=S3HttpError,
            *error_args,
            **error_kwargs,
    ):
        if Resp.status_code(d) != status_code:
            raise raise_error(*error_args, **error_kwargs)

    @staticmethod
    def ascertain_200_status_code(d):
        status_code = Resp.status_code(d, return_none_on_error)
        if status_code != 200:
            if not isinstance(d, dict):
                raise S3Not200StatusCodeError(
                    "Yeah, that's not even a dict, so doubt it's even a response."
                    f"I'm expecting a response over here. Instead I got a {type(d)}"
                )
            elif "ResponseMetadata" in d:
                raise S3Not200StatusCodeError(
                    f"Status code was not 200. Was {d['ResponseMetadata']}. "
                    f"ResponseMetadata is {d['ResponseMetadata']}"
                )
            else:
                raise S3Not200StatusCodeError(
                    f"Status code was not 200. In fact, the response dict didn't even have a ResponseMetadata key"
                )


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
    client_kwargs = get_configs()  # get (at least) aws_access_key_id and aws_secret_access_key
    r = S3BucketBaseReader(S3BucketBaseReader.mk_client(**resources_kwargs), bucket='bucket_name', prefix='my_stuff/')
    list(r)  # will list file and folder names
    r['my_stuff/music/']  # will give you another S3BucketBaseReader for that "subfolder"
    r['my_stuff/music/with_meaning.mp3']  # will give you the response object for the contents of the file
    ```
    """

    client: BaseClient
    bucket: str
    prefix: str = ""
    with_files: bool = True
    with_directories: bool = True

    def file_obj_for_key(self, k) -> dict:
        try:
            return self._source.get_object(Bucket=self.bucket, Key=k)
        except Exception as e:
            raise GetItemForKeyError(f"Problem retrieving value for key: {k}")

    def dir_obj_for_key(self, k) -> KvReader:
        # print(f"{id(self)}")
        # if hasattr(self.__class__, '_cls_trans'):
        #     cls = type(self.__class__.__name__, (), {})
        #     self.__class__._cls_trans(cls)
        # else:
        #     cls = self.__class__
        cls = self.__class__
        return cls(
            client=self._source,
            bucket=self.bucket,
            prefix=k,
            with_files=self.with_files,
            with_directories=self.with_directories,
        )

    def __post_init__(self):
        if self.prefix.endswith("*"):
            # msg = f"Ending with a * is a special and untested case. If you know what you're doing, go ahead though!"
            self.prefix = self.prefix[:-1]  # remove the *
            if self.prefix != '' and not self.prefix.endswith("/"):  # add the / if it's not there
                self.prefix += "/"
            _filt = dict(Prefix=self.prefix)  # without the Delimiter='/'
            if self.with_directories:
                self.with_directories = False
        else:
            if self.prefix != '' and not self.prefix.endswith("/"):
                self.prefix += "/"
            _filt = dict(Prefix=self.prefix, Delimiter="/")
        self.client = ensure_client(self.client)
        self._source = self.client
        self._filt = _filt
        self._prefix = (
            self.prefix
        )  # legacy: Some wrappers expect _prefix name.

    def is_valid_key(self, k) -> bool:
        return isinstance(k, str) and k.startswith(self.prefix)

    def validate_key(self, k):
        if not self.is_valid_key(k):
            if not isinstance(k, str):
                raise KeyNotValidError(
                    f"Key should be a string. Your key is: {k}"
                )
            elif not k.startswith(self.prefix):
                raise KeyNotValidError(
                    f"Prefix of key should be '{self.prefix}'. Your key is: {k}"
                )
            else:
                raise KeyNotValidError(f"Not a valid key: {k}")

    def __getitem__(self, k: str) -> Union[dict, KvReader]:
        self.validate_key(k)
        if isfile_key(k):
            return self.file_obj_for_key(k)
        else:  # assume it's a "directory"
            return self.dir_obj_for_key(k)

    def object_list_pages(self) -> Iterable[dict]:
        yield from self._source.get_paginator("list_objects").paginate(
            Bucket=self.bucket, **self._filt
        )

    def __iter__(self) -> Iterable[str]:
        for resp in self.object_list_pages():
            Resp.ascertain_200_status_code(resp)
            if self.with_files:
                yield from filter(
                    lambda k: not k.endswith("/"),
                    map(Resp.key, Resp.contents(resp)),
                )
                # for d in Resp.contents(resp):
                #     yield d['Key']
            if self.with_directories:
                yield from map(Resp.prefix, Resp.common_prefixes(resp))
                # for d in Resp.common_prefixes(resp):
                #     yield d['Prefix']

    def head_object(self, k) -> dict:
        self.validate_key(k)
        return self._source.head_object(Bucket=self.bucket, Key=k)

    def __contains__(self, k) -> bool:
        try:
            self.head_object(k)
            return True  # if all went well
        except KeyNotValidError as e:
            raise
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # The object does not exist.
                return False
            else:
                # Something else has gone wrong.
                raise

    @wraps(get_s3_client)
    @staticmethod
    def mk_client(**client_kwargs):
        return get_s3_client(**client_kwargs)


class S3BucketBasePersister(S3BucketBaseReader, KvPersister):
    def __setitem__(self, k, v) -> dict:
        self.validate_key(k)
        return self._source.put_object(Bucket=self.bucket, Key=k, Body=v)

    def __delitem__(self, k) -> dict:
        self.validate_key(k)
        return self._source.delete_object(Bucket=self.bucket, Key=k)
        # TODO: Figure out how to detect if the key existed or not from the return value, so one can use this
        #   to align with the common behavior of `del s[k]` when `k` doesn't exist.
        #   Would like to avoid having to do an additional request to do `if k in s: ...`


# Note: The classes below don't use the usual wrappers because these don't
#  handle the recursivity of S3BucketBaseReader
# TODO: Make wrappers that can follow recursive calls
#  (self.__class__ should be wrapped) if the self = cls(...) and cls is wrapped!)
class S3BucketReader(S3BucketBaseReader):
    def __getitem__(self, k: str) -> Union[dict, KvReader]:
        return super().__getitem__(self.prefix + k)

    def __iter__(self) -> Iterable[str]:
        n = len(self.prefix)
        yield from (k[n:] for k in super().__iter__())


class S3BucketPersister(S3BucketBasePersister):
    def __setitem__(self, k, v):
        super().__setitem__(self.prefix + k, v)

    def __delitem__(self, k):
        super().__delitem__(self.prefix + k)


@dataclass
class S3Collection(Collection):
    client: BaseClient

    def __post_init__(self):
        self.client = ensure_client(self.client)
        assert isinstance(self.client, BaseClient)
        self._source = self.client

    def __iter__(self) -> Iterable[str]:
        resp = self._source.list_buckets()
        Resp.ascertain_200_status_code(resp)
        yield from (bucket["Name"] for bucket in Resp.buckets(resp))

    @wraps(get_s3_client)
    @staticmethod
    def mk_client(**client_kwargs):
        return get_s3_client(**client_kwargs)


# TODO: Make some stores that have more convenient interfaces
#   (e.g. see existing py2store.store.s3_store and rewrite versions of those stores that use the
#   present new way)


def get_bucket_reader(s3_collection, bucket):
    return S3BucketBaseReader(s3_collection._source, bucket)


# Pattern: reader from collection + mapping maker.
# TODO: Make a special factory out of the pattern
class S3BaseReader(S3Collection, KvReader):
    item_getter = get_bucket_reader

    def __getitem__(self, k):
        return self.item_getter(k)


import pickle
from py2store.base import Store

# from py2store.persisters.s3_w_boto3 import S3BucketPersister
from py2store.paths import mk_relative_path_store

from py2store.trans import wrap_kvs


def _get_body_when_file(k, v):
    if isfile_key(k):
        Resp.ascertain_200_status_code(v)
        return Resp.body(v, on_error=f"Couldn't get the body from: {v}")
    else:
        return v


def _read_body_when_file(k, v):
    if isfile_key(k):
        return v.read()
    else:
        return v


def _bytes_when_file(k, v):
    v = _get_body_when_file(k, v)
    v = _read_body_when_file(k, v)
    return v


S3AbsPathBodyStore = wrap_kvs(
    S3BucketBasePersister,
    name="S3AbsPathBodyStore",
    postget=_get_body_when_file,
)

S3AbsPathBinaryStore = wrap_kvs(
    S3AbsPathBodyStore,
    name="S3AbsPathBinaryStore",
    postget=_read_body_when_file,
)

## Note: Alternative definition, using subclassing and checking value to determine if file (body) or not
# class S3AbsPathBinaryStore(S3AbsPathBodyStore):
#     def _obj_of_data(self, data):
#         body_or_dirobj = super()._obj_of_data(data)
#         if isinstance(body_or_dirobj, StreamingBody):
#             return body_or_dirobj.read()  # Note: This part has other options (like iter_chunks(), etc.)
#         else:
#             return body_or_dirobj


# S3BinaryStore = mk_relative_path_store(
#     S3AbsPathBinaryStore, __name__="S3BinaryStore", prefix_attr="prefix"
# )

S3BinaryReader = wrap_kvs(
    S3BucketReader,
    name="S3BinaryReader",
    postget=_bytes_when_file,
)

S3BinaryStore = wrap_kvs(
    S3BucketPersister,
    name="S3BinaryStore",
    postget=_bytes_when_file,
)


def asis_if_not_bytes(method):
    @wraps(method)
    def wrapped_method(self, data):
        if isinstance(data, bytes):
            return method(self, data)
        else:
            return data

    return wrapped_method


class S3TextStore(S3BinaryStore):
    def _obj_of_data(self, data):
        if isinstance(data, bytes):
            return data.decode()
        else:
            return data


S3StringStore = S3TextStore


class S3PickleStore(S3BinaryStore):
    def _obj_of_data(self, data):
        return pickle.loads(data)

    def _data_of_obj(self, obj):
        return pickle.dumps(obj)
