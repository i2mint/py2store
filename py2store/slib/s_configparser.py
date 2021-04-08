from configparser import ConfigParser, NoSectionError
from configparser import BasicInterpolation, ExtendedInterpolation
from functools import wraps
from io import BytesIO, StringIO

from py2store.trans import kv_wrap_persister_cls

# from py2store.signatures import Sig

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

# By default only in an empty line.
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


def persist_after_operation(method_func):
    @wraps(method_func)
    def _method_func(self, *args, **kwargs):
        output = method_func(self, *args, **kwargs)
        self.persist()
        return output

    return _method_func


def super_and_persist(super_cls, method_name):
    """
    To be able to do this:
    ```
    __setitem__ = super_and_persist(ConfigParser, '__setitem__')
    __delitem__ = super_and_persist(ConfigParser, '__delitem__')
    ```
    in your class definition block.

    I thought I needed to wrap more method this way, but as it turns out, I might not,
    so I prefer open code.
    """

    @persist_after_operation
    @wraps(getattr(super_cls, method_name))
    def method_func(self, *args, **kwargs):
        method_obj = getattr(super(ConfigStore, self), method_name)
        return method_obj(*args, **kwargs)

    return method_func


ConfigParserStore = kv_wrap_persister_cls(
    ConfigParser, name="ConfigParserStore"
)


# TODO: ConfigParser is already a mapping, but pros/cons of subclassing?
#   For instance, it has it's get method already, but it is not consistent with the get of collections.abc.Mapping
# TODO: Extend to a KvPersister (include __setitem__ and __delitem__)
#   Relevant methods: add_section, write, remove_section. Need to decide on auto-persistence.
#   In fact, the reader is already a writer (from ConfigParser), but need to manage persistence.
class ConfigStore(ConfigParserStore):
    r"""Persister (read, write, delete) for ini configs.

    You can read ini formated configurations with ConfigStore (though if you want to
    just read, you should use ConfigReader instead -- since ConfigReader disables
    write and delete operations.

    See ConfigReader for more examples of how to use ConfigStore.
    We'll mainly focus on write and delete operations here.

    >>> import os
    >>> from py2store.slib.s_configparser import ConfigStore, ConfigReader
    >>> ini_filepath = 'config_store_test.ini'
    >>> if os.path.isfile(ini_filepath):
    ...     os.remove(ini_filepath)
    >>>
    >>> os.path.isfile(ini_filepath)  # File doesn't exist
    False
    >>>
    >>> s = ConfigStore(ini_filepath)
    >>> list(s)  # There's always a default (by default empty)
    ['DEFAULT']
    >>>
    >>> os.path.isfile(ini_filepath)  # But the file still doesn't exist (the DEFAULT is virtual)
    False
    >>>
    >>> # Now let's make a config
    >>> s['nothing'] = {'special': 'about', 'number': 42}
    >>> list(s)
    ['DEFAULT', 'nothing']
    >>>
    >>> os.path.isfile(ini_filepath)  # But NOW the file exists (ConfigStore will automatically write to file)
    True
    >>> s['add'] = {'more': 'sections'}
    >>> list(s)
    ['DEFAULT', 'nothing', 'add']

    >>> # and yes, that config can now be read
    >>> config_reader = ConfigReader(ini_filepath)
    >>> list(config_reader)
    ['DEFAULT', 'nothing', 'add']
    >>>
    >>> config_reader['nothing']
    <Section: nothing>
    >>>
    >>> dict(config_reader['nothing'])  # note that 42 is now a string (that's the ini format for you!)
    {'special': 'about', 'number': '42'}
    >>> dict(config_reader['DEFAULT'])  # and DEFAULT is empty
    {}

    You can delete sections
    >>> del s['add']

    But you'll need to refresh your reader to see the effect.
    >>> list(config_reader)
    ['DEFAULT', 'nothing', 'add']
    >>> config_reader = ConfigReader(ini_filepath)
    >>> list(config_reader)
    ['DEFAULT', 'nothing']

    You can use `update` to write several sections at the same time.
    Note that existing sections will be completely overwritten.
    >>> s.update({'nothing': {'like': 'you'}, 'new_section': {'a': 'b', 'c': 'd'}})
    >>> ConfigReader(ini_filepath).to_dict()
    {'DEFAULT': {}, 'nothing': {'like': 'you'}, 'new_section': {'a': 'b', 'c': 'd'}}

    **Warning: On the other hand, updating a section will not persist the updates**

    Updates are automatically persisted at the top level, as shown in the example above.
    This means you can change a section entirely, but partial updates of a section
    will not be persisted.

    You'll see the updated section in the store.
    >>> s['nothing'].update({'something': 'else'})
    >>> dict(s['nothing'])
    {'like': 'you', 'something': 'else'}

    But it's not automatically persisted
    >>> dict(ConfigReader(ini_filepath)['nothing'])
    {'like': 'you'}

    ... unless you ask for it explicitly
    >>> s.persist()
    >>> dict(ConfigReader(ini_filepath)['nothing'])
    {'like': 'you', 'something': 'else'}

    # TODO: Could make section updates auto-persistent by wrapping configparser.SectionProxy

    For your convenience, the ConfigStore is also a context manager, that will,
    you guessed, persist stuff when (and only when) you exit it.

    >>> ConfigReader(ini_filepath).to_dict()
    {'DEFAULT': {}, 'nothing': {'like': 'you', 'something': 'else'}, 'new_section': {'a': 'b', 'c': 'd'}}
    >>> with ConfigStore(ini_filepath) as s:
    ...     del s['new_section']  # that's usually immediately persisted. This time, it'll wait to be
    ...     del s['nothing']['something']  # delete the something field of nothing section
    ...     s['nothing'].update({'like': 'that', 'ever': 'happened'})  # update 'like' config and add an 'ever' one
    >>> ConfigReader(ini_filepath).to_dict()
    {'DEFAULT': {}, 'nothing': {'like': 'that', 'ever': 'happened'}}

        """
    space_around_delimiters = True
    BasicInterpolation = BasicInterpolation
    ExtendedInterpolation = ExtendedInterpolation

    # @Sig.from_objs(['source', ConfigParser.__init__, ('target_kind', None)])  # need to add source and target_kind
    def __init__(
            self,
            source,
            *,
            defaults=None,
            dict_type=dict,
            allow_no_value=False,
            target_kind=None,
            **more_config_parser_kwargs,
    ):

        super().__init__(defaults, dict_type, allow_no_value, **more_config_parser_kwargs)

        self._within_context_manager = False

        if isinstance(source, str):
            if "\n" in source:
                self.read_string(source)
                source_kind = "string"
            else:
                self.read(source)
                source_kind = "filepath"
        elif isinstance(source, bytes):
            self.read_string(source.decode())
            source_kind = "bytes"
        elif isinstance(source, dict):
            self.read_dict(source)
            source_kind = "dict"
        elif hasattr(source, "read"):
            self.read_file(source)
            source_kind = "stream"
        else:
            self.read(source)
            source_kind = "unknown"
        self.source = source
        self.source_kind = source_kind
        self.target_kind = target_kind or source_kind

    def to_dict(self):
        return {
            section: dict(section_contents)
            for section, section_contents in self.items()
        }

    def get(self, k, default=None):
        """Needed because the Store.get didn't catch the NoSectionError"""
        try:
            return self[k]
        except KeyError:
            return default

    def persist(self):
        """Persists the data (if not in a context manager).
        Persists means to call
        """
        if not self._within_context_manager:
            if self.target_kind == "filepath":
                with open(self.source, "w") as fp:
                    return self.write(fp, self.space_around_delimiters)
            else:
                if self.target_kind == "stream":
                    target = self.source
                    return self.write(target, self.space_around_delimiters)
                elif self.target_kind in {"string", "bytes"}:
                    string_target = StringIO()
                    self.write(string_target, self.space_around_delimiters)
                    string_target.seek(0)
                    string_data = string_target.read()
                    if self.target_kind == "string":
                        return string_data
                    elif self.target_kind == "bytes":
                        return string_data.encode()
                    else:
                        raise ValueError(
                            f"Unknown target_kind: {self.target_kind}"
                        )
                elif self.target_kind == "dict":
                    return self.to_dict()
                else:
                    raise ValueError(
                        f"Unknown target_kind: {self.target_kind}"
                    )

    def __enter__(self):
        self._within_context_manager = True
        return self

    def __exit__(self, *exc_details):
        self._within_context_manager = False
        return self.persist()

    @persist_after_operation
    def __setitem__(self, k, v):
        super(ConfigStore, self).__setitem__(k, v)

    @persist_after_operation
    def __delitem__(self, k):
        super(ConfigStore, self).__delitem__(k)

    # __setitem__ = super_and_persist(ConfigParser, '__setitem__')
    # __delitem__ = super_and_persist(ConfigParser, '__delitem__')


class ConfigReader(ConfigStore):
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

    def persist(self):
        raise NotImplementedError("persist disabled for ConfigReader")

    def __setitem__(self, k, v):
        raise NotImplementedError("__setitem__ disabled for ConfigReader")

    def __delitem__(self, k):
        raise NotImplementedError("__delitem__ disabled for ConfigReader")


# TODO: Need to wrap SectionProxy to make this work, since the obj and data here are
#   those at a second level down.
#   That is, when you do s['section']['key'] = obj, _data_of_obj gets activated on s, not s['section'] as desired
# class ConfigStoreWithLists(ConfigStore):
#     def _data_of_obj(self, obj):
#         if isinstance(obj, list):
#             return '\n'.join(obj)
#         else:
#             return super()._data_of_obj(obj)
#
#     def _obj_of_data(self, data):
#         if data.startswith('\n'):
#             return data.split('\n')
#         else:
#             return super()._obj_of_data(data)


from typing import Mapping, Iterable, Generator, Union
import re


# TODO: postprocess_ini_section_items and preprocess_ini_section_items: Add comma separated possibility?
# TODO: Find out if configparse has an option to do this processing alreadys
def postprocess_ini_section_items(items: Union[Mapping, Iterable]) -> Generator:
    r"""Transform newline-separated string values into actual list of strings (assuming that intent)

    >>> section_from_ini = {
    ...     'name': 'aspyre',
    ...     'keywords': '\n\tdocumentation\n\tpackaging\n\tpublishing'
    ... }
    >>> section_for_python = dict(postprocess_ini_section_items(section_from_ini))
    >>> section_for_python
    {'name': 'aspyre', 'keywords': ['documentation', 'packaging', 'publishing']}

    """
    splitter_re = re.compile('[\n\r\t]+')
    if isinstance(items, Mapping):
        items = items.items()
    for k, v in items:
        if v.startswith('\n'):
            v = splitter_re.split(v[1:])
            v = [vv.strip() for vv in v if vv.strip()]
        yield k, v


# TODO: Find out if configparse has an option to do this processing alreadys
def preprocess_ini_section_items(items: Union[Mapping, Iterable]) -> Generator:
    """Transform list values into newline-separated strings, in view of writing the value to a ini formatted section
    >>> section = {
    ...     'name': 'aspyre',
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
