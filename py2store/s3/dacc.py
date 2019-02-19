from py2store.base import AbstractKeys, AbstractObjReader, AbstractObjWriter, AbstractObjStore
import boto3
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
    def __init__(self, name, aws_access_key_id, aws_secret_access_key,
                 endpoint_url=DFLT_AWS_S3_ENDPOINT,
                 verify=DFLT_BOTO_CLIENT_VERIFY,
                 config=DFLT_CONFIG):
        self.bucket_name = name
        self._resource_dict = dict(aws_access_key_id=aws_access_key_id,
                                   aws_secret_access_key=aws_secret_access_key,
                                   endpoint_url=endpoint_url,
                                   verify=verify,
                                   config=config)

    @lazyprop
    def _s3(self):
        return get_s3_resource(**self._resource_dict)

    @lazyprop
    def _s3_bucket(self):
        return self._s3.Bucket(self.bucket_name)

    def _obj_of_key(self, k):
        return self._s3.Object(self.bucket_name, key=k)


class S3BucketKeys(AbstractKeys, S3BucketDacc):

    def __iter__(self, prefix=''):
        return (x.key for x in self._s3_bucket.objects.filter(Prefix=prefix))

    # def __contains__(self, k):  # TODO: Find s3 specific more efficient way of doing __contains__
    #     pass

    # def __len__(self, k):  # TODO: Find s3 specific more efficient way of doing __len__
    #     pass


class S3BucketReader(AbstractObjReader, S3BucketDacc):

    def __getitem__(self, k):
        return self._obj_of_key(k).get()['Body'].read()


class S3BucketSource(S3BucketKeys, S3BucketReader):
    pass


class S3BucketWriter(AbstractObjWriter, S3BucketDacc):

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


class S3BucketStore(S3BucketSource, S3BucketWriter):
    pass
