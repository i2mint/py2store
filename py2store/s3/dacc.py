from py2store.base import AbstractKeys, AbstractObjReader, AbstractObjWriter, AbstractObjStore
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
    def __init__(self, bucket_name, s3_bucket):
        self.bucket_name = bucket_name
        self._s3_bucket = s3_bucket

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

    def _obj_of_key(self, k):
        return self._s3_bucket.Object(key=k)


class S3BucketKeys(AbstractKeys, S3BucketDacc):

    def __iter__(self, prefix=''):
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
