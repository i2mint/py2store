"""
Tools to map tuple-structured keys.
That is, converting from any of the following kinds of keys:
    * tuples (or list-like)
    * dicts
    * formatted/templated strings
    * dsv (Delimiter-Separated Values)

"""

# TODO: Add short docs
# TODO: Add SIMPLE (just one or two tests) doctests.
# TODO: Add randomized "bijectivity" tests (see _test_dsv_of_list for what I mean) if easy.

from functools import partial
from py2store.errors import KeyValidationError, _assert_condition

__assert_condition = partial(_assert_condition, err_cls=KeyValidationError)


def tuple_of_dict(d, fields):
    __assert_condition(len(fields) == len(d), f"len(d)={len(d)} but len(fields)={len(fields)}")
    return tuple(d[f] for f in fields)


def dict_of_tuple(d, fields):
    __assert_condition(len(fields) == len(d), f"len(d)={len(d)} but len(fields)={len(fields)}")
    return {f: x for f, x in zip(fields, d)}


def str_of_tuple(d, str_format):
    try:
        return str_format.format(*d)
    except Exception as e:
        raise KeyValidationError(e)


def tuple_of_str(d, compiled_regex):
    m = compiled_regex.match(d)
    if m:
        return m.groups()
    else:
        raise KeyValidationError(f"The string {d} didn't match the pattern {compiled_regex}")


def str_of_dict(d, str_format):
    try:
        return str_format.format(**d)
    except Exception as e:
        raise KeyValidationError(e)


def dict_of_str(d, compiled_regex):
    m = compiled_regex.match(d)
    if m:
        return m.groupdict()
    else:
        raise KeyValidationError(f"The string {d} didn't match the pattern {compiled_regex}")


def dsv_of_list(d, sep=','):
    """
    Converting a list of strings to a dsv (delimiter-separated values) string.

    Note that unlike most key mappers, there is no schema imposing size here. If you wish to impose a size
    validation, do so externally (we suggest using a decorator for that).

    Args:
        d: A list of component strings
        sep: The delimiter text used to separate a string into a list of component strings

    Returns:
        The delimiter-separated values (dsv) string for the input tuple

    >>> dsv_of_list(['a', 'brown', 'fox'], sep=' ')
    'a brown fox'
    >>> dsv_of_list(('jumps', 'over'), sep='/')  # for filepaths (and see that tuple inputs work too!)
    'jumps/over'
    >>> dsv_of_list(['Sat', 'Jan', '1', '1983'], sep=',')  # csv: the usual delimiter-separated values format
    'Sat,Jan,1,1983'
    >>> dsv_of_list(['First', 'Last'], sep=':::')  # a longer delimiter
    'First:::Last'
    >>> dsv_of_list(['singleton'], sep='@')  # when the list has only one element
    'singleton'
    >>> dsv_of_list([], sep='@')  # when the list is empty
    ''
    """
    return sep.join(d)


def list_of_dsv(d, sep=','):
    """
    Converting a dsv (delimiter-separated values) string to the list of it's components.

    Args:
        d: A (delimiter-separated values) string
        sep: The delimiter text used to separate the string into a list of component strings

    Returns:
        A list of component strings corresponding to the input delimiter-separated values (dsv) string

    >>> list_of_dsv('a brown fox', sep=' ')
    ['a', 'brown', 'fox']
    >>> tuple(list_of_dsv('jumps/over', sep='/'))  # for filepaths
    ('jumps', 'over')
    >>> list_of_dsv('Sat,Jan,1,1983', sep=',')  # csv: the usual delimiter-separated values format
    ['Sat', 'Jan', '1', '1983']
    >>> list_of_dsv('First:::Last', sep=':::')  # a longer delimiter
    ['First', 'Last']
    >>> list_of_dsv('singleton', sep='@')  # when the list has only one element
    ['singleton']
    >>> list_of_dsv('', sep='@')  # when the string is empty
    []
    """
    if not d:  # doing this, because split returns [''] on an empty string (bad choice if you ask me!)
        return []
    else:
        return d.split(sep)


def _test_dsv_of_list(n_tests=100, max_n_elements=10, max_sep_length=3):
    import random
    import string

    alphanumeric = string.digits + string.ascii_lowercase
    non_alphanumeric = ''.join(set(string.printable).difference(alphanumeric))

    def random_string(length=7, character_set=alphanumeric):
        return ''.join(random.choice(character_set) for _ in range(length))

    for i in range(n_tests):
        for n_elements in random.choice(range(1, max_n_elements + 1)):
            words = [x for x in random_string(n_elements, alphanumeric)]
            sep_length = random.choice(range(1, max_sep_length + 1))
            sep = random_string(sep_length, non_alphanumeric)
            dsv_line = dsv_of_list(words, sep)
            dsv_words = list_of_dsv(dsv_line, sep)
            assert all(dsv_words == words), f"Expected:\n\t{words}\nGot:\n\t{dsv_words}"


if __name__ == '__main__':
    _test_dsv_of_list()
