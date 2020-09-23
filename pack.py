from string import Formatter
import json
import urllib.request
from urllib.error import HTTPError
import re
from typing import Union, Mapping, Iterable, Generator
from configparser import ConfigParser
import os

DFLT_CONFIG_FILE = 'setup.cfg'
DFLT_CONFIG_SECTION = 'metadata'


# TODO: postprocess_ini_section_items and preprocess_ini_section_items: Add comma separated possibility?
# TODO: Find out if configparse has an option to do this processing alreadys
def postprocess_ini_section_items(items: Union[Mapping, Iterable]) -> Generator:
    r"""Transform newline-separated string values into actual list of strings (assuming that intent)

    >>> section_from_ini = {
    ...     'name': 'epythet',
    ...     'keywords': '\n\tdocumentation\n\tpackaging\n\tpublishing'
    ... }
    >>> section_for_python = dict(postprocess_ini_section_items(section_from_ini))
    >>> section_for_python
    {'name': 'epythet', 'keywords': ['documentation', 'packaging', 'publishing']}

    """
    splitter_re = re.compile('[\n\r\t]+')
    if isinstance(items, Mapping):
        items = items.items()
    for k, v in items:
        if v.startswith('\n'):
            v = splitter_re.split(v[1:])
            v = [vv.strip() for vv in v if vv.strip()]
            v = [vv for vv in v if not vv.startswith('#')]  # remove commented lines
        yield k, v


# TODO: Find out if configparse has an option to do this processing alreadys
def preprocess_ini_section_items(items: Union[Mapping, Iterable]) -> Generator:
    """Transform list values into newline-separated strings, in view of writing the value to a ini formatted section
    >>> section = {
    ...     'name': 'epythet',
    ...     'keywords': ['documentation', 'packaging', 'publishing']
    ... }
    >>> for_ini = dict(preprocess_ini_section_items(section))
    >>> print('keywords =' + for_ini['keywords'])  # doctest: +NORMALIZE_WHITESPACE
    keywords =
        documentation
        packaging
        publishing

    """
    if isinstance(items, Mapping):
        items = items.items()
    for k, v in items:
        if isinstance(v, list):
            v = '\n\t' + '\n\t'.join(v)
        yield k, v


def read_configs(
        config_file=DFLT_CONFIG_FILE,
        section=DFLT_CONFIG_SECTION,
        postproc=postprocess_ini_section_items):
    c = ConfigParser()
    c.read_file(open(config_file, 'r'))
    if section is None:
        d = dict(c)
        if postproc:
            d = {k: dict(postproc(v)) for k, v in c}
    else:
        d = dict(c[section])
        if postproc:
            d = dict(postproc(d))
    return d


def write_configs(
        configs,
        config_file=DFLT_CONFIG_FILE,
        section=DFLT_CONFIG_SECTION,
        preproc=preprocess_ini_section_items
):
    c = ConfigParser()
    if os.path.isfile(config_file):
        c.read_file(open(config_file, 'r'))
    c[section] = dict(preproc(configs))
    with open(config_file, 'w') as fp:
        c.write(fp)


dflt_formatter = Formatter()


def increment_version(version_str):
    version_nums = list(map(int, version_str.split('.')))
    version_nums[-1] += 1
    return '.'.join(map(str, version_nums))


DLFT_PYPI_PACKAGE_JSON_URL_TEMPLATE = 'https://pypi.python.org/pypi/{package}/json'


# TODO: Perhaps there's a safer way to analyze errors (and determine if the package exists or other HTTPError)
def current_pypi_version(
        package: str,
        url_template=DLFT_PYPI_PACKAGE_JSON_URL_TEMPLATE
) -> Union[str, None]:
    """
    Return version of package on pypi.python.org using json.

    ```
    > get_version('py2store')
    '0.0.7'
    ```

    :param package: Name of the package
    :return: A version (string) or None if there was an exception (usually means there
    """

    req = urllib.request.Request(url_template.format(package=package))
    try:
        r = urllib.request.urlopen(req)
        if r.code == 200:
            t = json.loads(r.read())
            releases = t.get('releases', [])
            if releases:
                return sorted(releases, key=lambda r: tuple(map(int, r.split('.'))))[-1]
        else:
            raise ValueError(f"response code was {r.code}")
    except HTTPError:
        return None  # to indicate (hopefully) that name doesn't exist
    except Exception:
        raise


def next_version_for_package(
        package: str,
        url_template=DLFT_PYPI_PACKAGE_JSON_URL_TEMPLATE,
        version_if_current_version_none='0.0.1'
) -> str:
    current_version = current_pypi_version(package, url_template)
    if current_version is not None:
        return increment_version(current_version)
    else:
        return version_if_current_version_none


def my_setup(**setup_kwargs):
    from setuptools import setup
    import json
    print("Setup params -------------------------------------------------------")
    print(json.dumps(setup_kwargs, indent=2))
    print("--------------------------------------------------------------------")
    setup(**setup_kwargs)


def ujoin(*args):
    """Join strings with the url seperator (/).

    Note that will add a / where it's missing (as in between 'https://pypi.org' and 'project/'),
    and only use one if two consecutive tokens use respectively end and start with a /
    (as in 'project/' and '/pipoke/').

    >>> ujoin('https://pypi.org', 'project/', '/pipoke/')
    'https://pypi.org/project/pipoke/'

    Extremal cases
    >>> ujoin('https://pypi.org')
    'https://pypi.org'
    >>> ujoin('https://pypi.org/')
    'https://pypi.org/'
    >>> ujoin('')
    ''
    >>> ujoin()
    ''
    """
    if len(args) == 0 or len(args[0]) == 0:
        return ''
    return ((args[0][0] == '/') * '/'  # prepend slash if first arg starts with it
            + '/'.join(x[(x[0] == '/'):(len(x) - (x[-1] == '/'))] for x in args)
            + (args[-1][-1] == '/') * '/')  # append slash if last arg ends with it


########### Partial and incremental formatting #########################################################################
class PartialFormatter(Formatter):
    """A string formatter that won't complain if the fields are only partially formatted.
    But note that you will lose the spec part of your template (e.g. in {foo:1.2f}, you'll loose the 1.2f
    if not foo is given -- but {foo} will remain).
    """

    def get_value(self, key, args, kwargs):
        try:
            return super().get_value(key, args, kwargs)
        except KeyError:
            return '{' + key + '}'

    def format_fields_set(self, s):
        return {x[1] for x in self.parse(s) if x[1]}


partial_formatter = PartialFormatter()


# TODO: For those who love algorithmic optimization, there's some wasted to cut out here below.

def _unformatted(d):
    for k, v in d.items():
        if isinstance(v, str) and len(partial_formatter.format_fields_set(v)) > 0:
            yield k


def _fields_to_format(d):
    for k, v in d.items():
        if isinstance(v, str):
            yield from partial_formatter.format_fields_set(v)


def format_str_vals_of_dict(d, *, max_formatting_loops=10, **kwargs):
    """

    :param d:
    :param max_formatting_loops:
    :param kwargs:
    :return:

    >>> d = {
    ...     'filepath': '{root}/{file}.{ext}',
    ...     'ext': 'txt'
    ... }
    >>> format_str_vals_of_dict(d, root='ROOT', file='FILE')
    {'filepath': 'ROOT/FILE.txt', 'ext': 'txt'}

    Note that if the input mapping `d` and the kwargs have a conflict, the mapping version is used!

    >>> format_str_vals_of_dict(d, root='ROOT', file='FILE', ext='will_not_be_used')
    {'filepath': 'ROOT/FILE.txt', 'ext': 'txt'}

    But if you want to override an input mapping, you can -- the usual way:
    >>> format_str_vals_of_dict(dict(d, ext='will_be_used'), root='ROOT', file='FILE')
    {'filepath': 'ROOT/FILE.will_be_used', 'ext': 'will_be_used'}

    If you don't provide enough fields to satisfy all the format fields in the values of `d`,
    you'll be told to bugger off.

    >>> format_str_vals_of_dict(d, root='ROOT')
    Traceback (most recent call last):
    ...
    ValueError: I won't be able to complete that. You'll need to provide the values for:
      file

    And it's recursive...
    >>> d = {
    ...     'filepath': '{root}/{filename}',
    ...     'filename': '{file}.{ext}'
    ... }
    >>> my_configs = {'root': 'ROOT', 'file': 'FILE', 'ext': 'EXT'}
    >>> format_str_vals_of_dict(d, **my_configs)
    {'filepath': 'ROOT/FILE.EXT', 'filename': 'FILE.EXT'}

    # TODO: Could make the above work if filename is give, but not file nor ext! At least as an option.

    """
    d = dict(**d)  # make a shallow copy
    # The defaults (kwargs) cannot overlap with any keys of d, so:
    kwargs = {k: kwargs[k] for k in set(kwargs) - set(d)}

    provided_fields = set(d) | set(kwargs)
    missing_fields = set(_fields_to_format(d)) - provided_fields

    if missing_fields:
        raise ValueError("I won't be able to complete that. You'll need to provide the values for:\n" +
                         f"  {', '.join(missing_fields)}")

    for i in range(max_formatting_loops):
        unformatted = set(_unformatted(d))

        if unformatted:
            for k in unformatted:
                d[k] = partial_formatter.format(d[k], **kwargs, **d)
        else:
            break
    else:
        raise ValueError(f"There are still some unformatted fields, "
                         f"but I reached my max {max_formatting_loops} allowed loops. " +
                         f"Those fields are: {set(_fields_to_format(d)) - (set(d) | set(kwargs))}")

    return d
