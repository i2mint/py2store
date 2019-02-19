from botocore.client import Config

DFLT_AWS_S3_ENDPOINT = "https://s3.amazonaws.com"
DFLT_BOTO_CLIENT_VERIFY = None
DFLT_SIGNATURE_VERSION = 's3v4'

DFLT_CONFIG = Config(signature_version=DFLT_SIGNATURE_VERSION)
