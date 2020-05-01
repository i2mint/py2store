from configparser import ConfigParser
from configparser import BasicInterpolation, ExtendedInterpolation

from py2store.utils.signatures import update_signature_with_signatures_from_funcs as change_sig

from py2store.base import KvReader

_test_config_str = """[Simple Values]
key=value
spaces in keys=allowed
spaces in values=allowed as well
spaces around the delimiter = obviously
you can also use : to delimit keys from values

[All Values Are Strings]
values like this: 1000000
or this: 3.14159265359
are they treated as numbers? : no
integers, floats and booleans are held as: strings
can use the API to get converted values directly: true

[Multiline Values]
chorus: I'm a lumberjack, and I'm okay
    I sleep all night and I work all day

[No Values]
key_without_value
empty string value here =

[You can use comments]
# like this
; or this

# By default only in an empty line.https://otosense.slack.com/archives/CB11V1D2Q
# Inline comments can be harmful because they prevent users
# from using the delimiting characters as parts of values.
# That being said, this can be customized.

    [Sections Can Be Indented]
        can_values_be_as_well = True
        does_that_mean_anything_special = False
        purpose = formatting for readability
        multiline_values = are
            handled just fine as
            long as they are indented
            deeper than the first line
            of a value
        # Did I mention we can indent comments, too?
"""


# TODO: ConfigParser is already a mapping, but pros/cons of subclassing?
#   For instance, it has it's get method already, but it is not consistent with the get of collections.abc.Mapping
# TODO: Extend to a KvPersister (include __setitem__ and __delitem__)
#   Relevant methods: add_section, write, remove_section. Need to decide on auto-persistence.
#   In fact, the reader is already a writer (from ConfigParser), but need to manage persistence.
class ConfigReader(KvReader, ConfigParser):
    r"""A KvReader to read config files
    >>> from py2store.slib.s_configparser import ConfigReader
    >>>
    >>> # from a (pretend) file
    >>> from io import BytesIO, StringIO
    >>> file_content_bytes = b'''
    ... [Paths]
    ... home_dir: /Users
    ... my_dir: %(home_dir)s/lumberjack
    ... my_pictures: %(my_dir)s/Pictures
    ...
    ... [Escape]
    ... gain: 80%%  # use a %% to escape the % sign (% is the only character that needs to be escaped)'''
    >>> c = ConfigReader(file_content_bytes)  # get configs from the bytes
    >>> list(c)
    ['DEFAULT', 'Paths', 'Escape']
    >>> ######## From a (pretend) file (pointer) ########
    >>> # Usually, you write your configs in a file and give ConfigReader the filepath, or open file pointer...
    >>> pretend_file_pointer = StringIO(file_content_bytes.decode())
    >>> c = ConfigReader(pretend_file_pointer)
    >>> list(c)
    ['DEFAULT', 'Paths', 'Escape']
    >>> c['Paths']  # gives you a configparser.Section object
    <Section: Paths>
    >>> # A configparser.Section is a mapping. Let's see the keys
    >>> list(c['Paths'])
    ['home_dir', 'my_dir', 'my_pictures']
    >>> # here's a quick way to see both keys and values. Note how the home_dir interpolation was performed!
    >>> dict(c['Paths'])
    {'home_dir': '/Users', 'my_dir': '/Users/lumberjack', 'my_pictures': '/Users/lumberjack/Pictures'}
    >>>
    >>> ######## Get configs from a dict ########
    >>> config_dict = {'section1': {'key1': 'value1'},
    ...                'section2': {'keyA': 'valueA', 'keyB': 'valueB'},
    ...                'section3': {'foo': 'x', 'bar': 'y','baz': 'z'}}
    >>> c = ConfigReader(config_dict)
    >>>
    >>> assert list(c) == ['DEFAULT', 'section1', 'section2', 'section3']
    >>> assert list(c['section3']) == ['foo', 'bar', 'baz']
    >>>
    >>> ######## Get configs from a string ########
    >>> from py2store.slib.s_configparser import _test_config_str
    >>> c = ConfigReader(_test_config_str, allow_no_value=True)
    >>> list(c)
    ['DEFAULT', 'Simple Values', 'All Values Are Strings', 'Multiline Values', 'No Values', 'You can use comments', 'Sections Can Be Indented']
    >>> list(c['Simple Values'])
    ['key', 'spaces in keys', 'spaces in values', 'spaces around the delimiter', 'you can also use']
    """

    BasicInterpolation = BasicInterpolation
    ExtendedInterpolation = ExtendedInterpolation

    @change_sig(ConfigParser)
    def __init__(self, source, defaults=None, dict_type=dict, allow_no_value=False, **kwargs):
        super().__init__(defaults, dict_type, allow_no_value, **kwargs)
        self.source = source
        if isinstance(source, str):
            if '\n' in source:
                self.read_string(source)
            else:
                self.read(source)
        elif isinstance(source, bytes):
            self.read_string(source.decode())
        elif isinstance(source, dict):
            self.read_dict(source)
        elif hasattr(source, 'read'):
            self.read_file(source)
        else:
            self.read(source)

    def to_dict(self):
        return {section: dict(section_contents) for section, section_contents in self.items()}
