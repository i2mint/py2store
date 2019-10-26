import os
import random
import string
from functools import reduce
from operator import add

from py2store.key_mappers.tuples import dict_of_tuple, str_of_tuple, dsv_of_list
from py2store.key_mappers.str_utils import n_format_params_in_str_format, empty_arg_and_kwargs_for_format

# Note: Probably want to use another package for generation of fake data.
#   For example, https://github.com/joke2k/faker

lower_case_letters = string.ascii_lowercase
alphanumeric = string.digits + lower_case_letters
non_alphanumeric = ''.join(set(string.printable).difference(alphanumeric))


def random_word(length, alphabet, concat_func=add):
    """Make a random word by concatenating randomly drawn elements from alphabet together
    Args:
        length: Length of the word
        alphabet: Alphabet to draw from
        concat_func: The concatenation function (e.g. + for strings and lists)

    Note: Repeated elements in alphabet will have more chances of being drawn.

    Returns:
        A word (whose type depends on what concatenating elements from alphabet produces).

    Not making this a proper doctest because I don't know how to seed the global random temporarily
    >>> t = random_word(4, 'abcde');  # e.g. 'acae'
    >>> t = random_word(5, ['a', 'b', 'c']);  # e.g. 'cabba'
    >>> t = random_word(4, [[1, 2, 3], [40, 50], [600], [7000]]);  # e.g. [40, 50, 7000, 7000, 1, 2, 3]
    >>> t = random_word(4, [1, 2, 3, 4]);  # e.g. 13 (because adding numbers...)
    >>> # ... sometimes it's what you want:
    >>> t = random_word(4, [2 ** x for x in range(8)]);  # e.g. 105 (binary combination)
    >>> t = random_word(4, [1, 2, 3, 4], concat_func=lambda x, y: str(x) + str(y));  # e.g. '4213'
    >>> t = random_word(4, [1, 2, 3, 4], concat_func=lambda x, y: int(str(x) + str(y)));  # e.g. 3432
    """
    if isinstance(alphabet, bytes) or isinstance(alphabet[0], bytes):
        # convert to list of bytes, or the function will return ints instead of bytes
        alphabet = _list_of_bytes_singletons(alphabet)
    return reduce(concat_func, (random.choice(alphabet) for _ in range(length)))


def _list_of_bytes_singletons(bytes_alphabet):
    """Convert to list of bytes, or the function will return ints instead of bytes"""
    return list(map(lambda x: bytes([x]), bytes_alphabet))


def random_string(length=7, alphabet=lower_case_letters):
    """Same as random_word, but it optimized for strings
    (5-10% faster for words of length 7, 25-30% faster for words of size 1000)"""
    return ''.join(random.choice(alphabet) for _ in range(length))


def random_word_gen(word_size_range=(1, 10), alphabet=lower_case_letters, n=100):
    """Random string generator
    Args:
        word_size_range: An int, 2-tuple of ints, or list-like object that defines the choices of word sizes
        alphabet: A string or iterable defining the alphabet to draw from
        n: The number of elements the generator will yield

    Returns:
        Random string generator
    """
    if isinstance(word_size_range, int):
        word_size_range = range(1, word_size_range + 1)
    elif not isinstance(word_size_range, range):
        word_size_range = range(*word_size_range)

    for _ in range(n):
        length = random.choice(word_size_range)
        yield random_word(length, alphabet)


def random_tuple_gen(tuple_length=3, word_size_range=(1, 10), alphabet=lower_case_letters, n: int = 100):
    """Random tuple (of strings) generator

    Args:
        tuple_length: The length of the tuples generated
        word_size_range: An int, 2-tuple of ints, or list-like object that defines the choices of word sizes
        alphabet: A string or iterable defining the alphabet to draw from
        n: The number of elements the generator will yield

    Returns:
        Random tuple (of strings) generator
    """
    for _ in range(n):
        yield tuple(random_word_gen(word_size_range, alphabet, tuple_length))


def random_dict_gen(fields=('a', 'b', 'c'), word_size_range=(1, 10), alphabet=lower_case_letters, n: int = 100):
    """Random dict (of strings) generator

    Args:
        fields: Field names for the random dicts
        word_size_range: An int, 2-tuple of ints, or list-like object that defines the choices of word sizes
        alphabet: A string or iterable defining the alphabet to draw from
        n: The number of elements the generator will yield

    Returns:
        Random dict (of strings) generator
    """
    tuple_length = len(fields)
    yield from (dict_of_tuple(x, fields)
                for x in random_tuple_gen(tuple_length, word_size_range, alphabet, n))


def random_formatted_str_gen(format_string='root/{}/{}_{}.test',
                             word_size_range=(1, 10), alphabet=lower_case_letters, n=100):
    """Random formatted string generator

    Args:
        format_string: A format string
        word_size_range: An int, 2-tuple of ints, or list-like object that defines the choices of word sizes
        alphabet: A string or iterable defining the alphabet to draw from
        n: The number of elements the generator will yield

    Returns:
        Yields random strings of the format defined by format_string

    Examples:
        # >>> list(random_formatted_str_gen('root/{}/{}_{}.test', (2, 5), 'abc', n=5))
        [('root/acba/bb_abc.test',),
         ('root/abcb/cbbc_ca.test',),
         ('root/ac/ac_cc.test',),
         ('root/aacc/ccbb_ab.test',),
         ('root/aab/abb_cbab.test',)]

    >>> # The following will be made not random (by restricting the constraints to "no choice"
    >>> # ... this is so that we get consistent outputs to assert for the doc test.
    >>>
    >>> # Example with automatic specification
    >>> list(random_formatted_str_gen('root/{}/{}_{}.test', (3, 4), 'a', n=2))
    [('root/aaa/aaa_aaa.test',), ('root/aaa/aaa_aaa.test',)]
    >>>
    >>> # Example with manual specification
    >>> list(random_formatted_str_gen('indexed field: {0}: named field: {name}', (2, 3), 'z', n=1))
    [('indexed field: zz: named field: zz',)]
    """
    args_template, kwargs_template = empty_arg_and_kwargs_for_format(format_string)
    n_args = len(args_template)
    args_gen = random_tuple_gen(n_args, word_size_range, alphabet, n)
    kwargs_gen = random_dict_gen(kwargs_template.keys(), word_size_range, alphabet, n)
    yield from zip(format_string.format(*args, **kwargs) for args, kwargs in zip(args_gen, kwargs_gen))


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
