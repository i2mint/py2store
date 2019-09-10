import os
import random
import string

from py2store.key_mappers.tuples import dict_of_tuple, str_of_tuple, dsv_of_list
from py2store.key_mappers.str_utils import n_format_params_in_str_format

lower_case_letters = string.ascii_lowercase
alphanumeric = string.digits + lower_case_letters
non_alphanumeric = ''.join(set(string.printable).difference(alphanumeric))


def random_string(length=7, character_set=lower_case_letters):
    return ''.join(random.choice(character_set) for _ in range(length))


def random_string_gen(word_size_range=(1, 10), character_set=lower_case_letters, n=100):
    if isinstance(word_size_range, int):
        word_size_range = range(1, word_size_range + 1)
    elif not isinstance(word_size_range, range):
        word_size_range = range(*word_size_range)

    for _ in range(n):
        n_characters = random.choice(word_size_range)
        yield random_string(n_characters, character_set)


def random_tuple_gen(tuple_length=3, word_size_range=(1, 10), character_set=lower_case_letters, n: int = 100):
    for _ in range(tuple_length):
        yield tuple(random_string_gen(word_size_range, character_set, n))


def random_dict_gen(fields=('a', 'b', 'c'), word_size_range=(1, 10), character_set=lower_case_letters, n=100):
    tuple_length = len(fields)
    yield from (dict_of_tuple(x, fields)
                for x in random_tuple_gen(tuple_length, word_size_range, character_set, n))


def random_formatted_str_gen(format_string='root/{}/{}_{}.test',
                           word_size_range=(1, 10), character_set=lower_case_letters, n=100):
    n = n_format_params_in_str_format(format_string)



    # tuple_length = len(fields)
    # yield from (str_of_tuple(x, fields)
    #             for x in random_tuple_gen(tuple_length, word_size_range, character_set, n))


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
