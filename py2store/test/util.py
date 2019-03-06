import os


########################################################################################################################
# s3 utils

def extract_s3_access_info(access_dict):
    return {'bucket_name': access_dict['bucket'],
            'aws_access_key_id': access_dict['access'],
            'aws_secret_access_key': access_dict['secret']}


def _s3_env_var_name(kind, perm='RO'):
    kind = kind.upper()
    perm = perm.upper()
    assert kind in {'BUCKET', 'ACCESS', 'SECRET'}, "kind should be in {'BUCKET', 'ACCESS', 'SECRET'}"
    assert perm in {'RW', 'RO'}, "perm should be in {'RW', 'RO'}"
    return "S3_TEST_{kind}_{perm}".format(kind=kind, perm=perm)


def get_s3_test_access_info_from_env_vars(perm=None):
    if perm is None:
        try:
            return get_s3_test_access_info_from_env_vars(perm='RO')
        except LookupError:
            return get_s3_test_access_info_from_env_vars(perm='RW')
    else:
        access_keys = dict()
        for kind in {'BUCKET', 'ACCESS', 'SECRET'}:
            k = _s3_env_var_name(kind, perm)
            if k not in os.environ:
                raise LookupError("Couldn't find the environment variable: {}".format(k))
            else:
                access_keys[kind.lower()] = os.environ[k]
        return extract_s3_access_info(access_keys)
