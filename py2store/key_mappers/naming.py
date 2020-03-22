"""
This module is about generating, validating, and operating on (parametrized) fields (i.e. stings, e.g. paths).
"""

import re
import os
from functools import partial, wraps
from types import MethodType

from py2store.utils.signatures import set_signature_of_func
from py2store.errors import KeyValidationError, _assert_condition

assert_condition = partial(_assert_condition, err_cls=KeyValidationError)

path_sep = os.path.sep

base_validation_funs = {
    "be a": isinstance,
    "be in": lambda val, check_val: val in check_val,
    "be at least": lambda val, check_val: val >= check_val,
    "be more than": lambda val, check_val: val > check_val,
    "be no more than": lambda val, check_val: val <= check_val,
    "be less than": lambda val, check_val: val < check_val,
}

dflt_validation_funs = base_validation_funs
dflt_all_kwargs_should_be_in_validation_dict = False
dflt_ignore_misunderstood_validation_instructions = False

dflt_arg_pattern = r'.+'

day_format = "%Y-%m-%d"
day_format_pattern = re.compile('\d{4}-\d{2}-\d{2}')

capture_template = '({format})'
named_capture_template = '(?P<{name}>{format})'

fields_re = re.compile('(?<={)[^}]+(?=})')


def validate_kwargs(kwargs_to_validate,
                    validation_dict,
                    validation_funs=None,
                    all_kwargs_should_be_in_validation_dict=False,
                    ignore_misunderstood_validation_instructions=False
                    ):
    """
    Utility to validate a dict. It's main use is to validate function arguments (expressing the validation checks
    in validation_dict) by doing validate_kwargs(locals()), usually in the beginning of the function
    (to avoid having more accumulated variables than we need in locals())
    :param kwargs_to_validate: as the name implies...
    :param validation_dict: A dict specifying what to validate. Keys are usually name of variables (when feeding
        locals()) and values are dicts, themselves specifying check:check_val pairs where check is a string that
        points to a function (see validation_funs argument) and check_val is an object that the kwargs_to_validate
        value will be checked against.
    :param validation_funs: A dict of check:check_function(val, check_val) where check_function is a function returning
        True if val is valid (with respect to check_val).
    :param all_kwargs_should_be_in_validation_dict: If True, will raise an error if kwargs_to_validate contains
        keys that are not in validation_dict.
    :param ignore_misunderstood_validation_instructions: If True, will raise an error if validation_dict contains
        a key that is not in validation_funs (safer, since if you mistype a key in validation_dict, the function will
        tell you so!
    :return: True if all the validations passed.

    >>> validation_dict = {
    ...     'system': {
    ...         'be in': {'darwin', 'linux'}
    ...     },
    ...     'fv_version': {
    ...         'be a': int,
    ...         'be at least': 5
    ...     }
    ... }
    >>> validate_kwargs({'system': 'darwin'}, validation_dict)
    True
    >>> try:
    ...     validate_kwargs({'system': 'windows'}, validation_dict)
    ... except AssertionError as e:
    ...     assert str(e).startswith('system must be in')  # omitting the set because inconsistent order
    >>> try:
    ...     validate_kwargs({'fv_version': 9.9}, validation_dict)
    ... except AssertionError as e:
    ...     print(e)
    fv_version must be a <class 'int'>
    >>> try:
    ...     validate_kwargs({'fv_version': 4}, validation_dict)
    ... except AssertionError as e:
    ...     print(e)
    fv_version must be at least 5
    >>> validate_kwargs({'fv_version': 6}, validation_dict)
    True
    """
    validation_funs = dict(base_validation_funs or {}, **(validation_funs or {}))
    for var, val in kwargs_to_validate.items():  # for every (var, val) pair of kwargs
        if var in validation_dict:  # if var is in the validation_dict
            for check, check_val in validation_dict[var].items():  # for every (key, val) of this dict
                if check in base_validation_funs:  # if you have a validation check for it
                    if not validation_funs[check](val, check_val):  # check it's valid
                        raise AssertionError("{} must {} {}".format(var, check, check_val))  # and raise an error if not
                elif not ignore_misunderstood_validation_instructions:  # should ignore if check not understood?
                    raise AssertionError("I don't know what to do with the validation check '{}'".format(
                        check
                    ))
        elif all_kwargs_should_be_in_validation_dict:  # should all variables have checks?
            raise AssertionError("{} wasn't in the validation_dict")
    return True


def namedtuple_to_dict(nt):
    """
    >>> from collections import namedtuple
    >>> NT = namedtuple('MyTuple', ('foo', 'hello'))
    >>> nt = NT(1, 42)
    >>> nt
    MyTuple(foo=1, hello=42)
    >>> d = namedtuple_to_dict(nt)
    >>> d
    {'foo': 1, 'hello': 42}
    """
    return {field: getattr(nt, field) for field in nt._fields}


def dict_to_namedtuple(d, namedtuple_obj=None):
    """
    >>> from collections import namedtuple
    >>> NT = namedtuple('MyTuple', ('foo', 'hello'))
    >>> nt = NT(1, 42)
    >>> nt
    MyTuple(foo=1, hello=42)
    >>> d = namedtuple_to_dict(nt)
    >>> d
    {'foo': 1, 'hello': 42}
    >>> dict_to_namedtuple(d)
    NamedTupleFromDict(foo=1, hello=42)
    >>> dict_to_namedtuple(d, nt)
    MyTuple(foo=1, hello=42)
    """
    if namedtuple_obj is None:
        namedtuple_obj = 'NamedTupleFromDict'
    if isinstance(namedtuple_obj, str):
        namedtuple_name = namedtuple_obj
        namedtuple_cls = namedtuple(namedtuple_name, tuple(d.keys()))
    elif isinstance(namedtuple_obj, tuple) and hasattr(namedtuple_obj, '_fields'):
        namedtuple_cls = namedtuple_obj.__class__
    elif isinstance(namedtuple_obj, type):
        namedtuple_cls = namedtuple_obj
    else:
        raise TypeError(f"Can't resolve the nametuple class specification: {namedtuple_obj}")

    return namedtuple_cls(**d)


def update_fields_of_namedtuple(nt: tuple, *, name_of_output_type=None, remove_fields=(), **kwargs):
    """Replace fields of namedtuple
    >>> from collections import namedtuple
    >>> NT = namedtuple('NT', ('a', 'b', 'c'))
    >>> nt = NT(1,2,3)
    >>> nt
    NT(a=1, b=2, c=3)
    >>> update_fields_of_namedtuple(nt, c=3000)  # replacing a single field
    NT(a=1, b=2, c=3000)
    >>> update_fields_of_namedtuple(nt, c=3000, a=1000)  # replacing two fields
    NT(a=1000, b=2, c=3000)
    >>> update_fields_of_namedtuple(nt, a=1000, c=3000)  # see that the original order doesn't change
    NT(a=1000, b=2, c=3000)
    >>> update_fields_of_namedtuple(nt, b=2000, d='hello')  # replacing one field and adding a new one
    UpdatedNT(a=1, b=2000, c=3, d='hello')
    >>> # Now let's try controlling the name of the output type, remove fields, and add new ones
    >>> update_fields_of_namedtuple(nt, name_of_output_type='NewGuy', remove_fields=('a', 'c'), hello='world')
    NewGuy(b=2, hello='world')
    """

    output_type_can_be_the_same_as_input_type = (not remove_fields) and set(kwargs.keys()).issubset(nt._fields)
    d = dict(namedtuple_to_dict(nt), **kwargs)
    for f in remove_fields:
        d.pop(f)

    if output_type_can_be_the_same_as_input_type and name_of_output_type is None:
        return dict_to_namedtuple(d, nt.__class__)
    else:
        name_of_output_type = name_of_output_type or f'Updated{nt.__class__.__name__}'
        return dict_to_namedtuple(d, name_of_output_type)


empty_field_p = re.compile('{}')


def get_fields_from_template(template):
    """
    Get list from {item} items of template string
    :param template: a "template" string (a string with {item} items
    -- the kind that is used to mark token for str.format)
    :return: a list of the token items of the string, in the order they appear
    >>> get_fields_from_template('this{is}an{example}of{a}template')
    ['is', 'example', 'a']
    """
    # TODO: Need to use the string module, and need to auto-name the fields instead of refusing unnamed
    assert not empty_field_p.search(template), "All fields must be named: That is, no empty {} allowed"
    return fields_re.findall(template)


# until_slash = "[^" + path_sep + "]+"
# until_slash_capture = '(' + until_slash + ')'

def mk_format_mapping_dict(format_dict, required_keys, sep=path_sep):
    until_sep = "[^" + re.escape(sep) + "]+"
    new_format_dict = format_dict.copy()
    for k in required_keys:
        if k not in new_format_dict:
            new_format_dict[k] = until_sep
    return new_format_dict


def mk_capture_patterns(mapping_dict):
    new_mapping_dict = dict()
    for k, v in mapping_dict.items():
        new_v = capture_template.format(format=v)
        new_mapping_dict[k] = new_v
    return new_mapping_dict


def mk_named_capture_patterns(mapping_dict):
    new_mapping_dict = dict()
    for k, v in mapping_dict.items():
        new_v = named_capture_template.format(name=k, format=v)
        new_mapping_dict[k] = new_v
    return new_mapping_dict


def template_to_pattern(mapping_dict, template):
    if mapping_dict:
        p = re.compile("{}".format("|".join(['{' + re.escape(x) + '}' for x in list(mapping_dict.keys())])))
        return p.sub(lambda x: mapping_dict[x.string[(x.start() + 1):(x.end() - 1)]], template)
    else:
        return template


def mk_extract_pattern(template, format_dict=None, named_capture_patterns=None, name=None):
    format_dict = format_dict or {}
    named_capture_patterns = named_capture_patterns or mk_named_capture_patterns(format_dict)
    assert name is not None
    mapping_dict = dict(format_dict, **{name: named_capture_patterns[name]})
    p = re.compile("{}".format("|".join(
        ['{' + re.escape(x) + '}' for x in list(mapping_dict.keys())])))

    return re.compile(p.sub(lambda x: mapping_dict[x.string[(x.start() + 1):(x.end() - 1)]], template))


def mk_pattern_from_template_and_format_dict(template, format_dict=None):
    """Make a compiled regex to match template

    Args:
        template: A format string
        format_dict: A dict whose keys are template fields and values are regex strings to capture them

    Returns: a compiled regex

    >>> mk_pattern_from_template_and_format_dict('{here}/and/{there}')
    re.compile('(?P<here>[^/]+)/and/(?P<there>[^/]+)')
    >>> p = mk_pattern_from_template_and_format_dict('{here}/and/{there}', {'there': '\d+'})
    >>> p
    re.compile('(?P<here>[^/]+)/and/(?P<there>\\\d+)')
    >>> type(p)
    <class 're.Pattern'>
    >>> p.match('HERE/and/1234').groupdict()
    {'here': 'HERE', 'there': '1234'}
    """
    format_dict = format_dict or {}

    fields = get_fields_from_template(template)
    format_dict = mk_format_mapping_dict(format_dict, fields)
    named_capture_patterns = mk_named_capture_patterns(format_dict)
    return re.compile(template_to_pattern(named_capture_patterns, template))


def mk_prefix_templates_dicts(template):
    fields = get_fields_from_template(template)
    prefix_template_dict_including_name = dict()
    none_and_fields = [None] + fields
    for name in none_and_fields:
        if name == fields[-1]:
            prefix_template_dict_including_name[name] = template
        else:
            if name is None:
                next_name = fields[0]
            else:
                next_name = fields[1 + next(i for i, _name in enumerate(fields) if _name == name)]
            p = '{' + next_name + '}'
            template_idx_of_next_name = re.search(p, template).start()
            prefix_template_dict_including_name[name] = template[:template_idx_of_next_name]

    prefix_template_dict_excluding_name = dict()
    for i, name in enumerate(fields):
        prefix_template_dict_excluding_name[name] = prefix_template_dict_including_name[none_and_fields[i]]
    prefix_template_dict_excluding_name[None] = template

    return prefix_template_dict_including_name, prefix_template_dict_excluding_name


def mk_kwargs_trans(**trans_func_for_key):
    """ Make a dict transformer from functions that depends solely on keys (of the dict to be transformed)
    Used to easily make process_kwargs and process_info_dict arguments for LinearNaming.
    """
    assert all(map(callable, trans_func_for_key.values())), "all argument values must be callable"

    def key_based_val_trans(**kwargs):
        for k, v in kwargs.items():
            if k in trans_func_for_key:
                kwargs[k] = trans_func_for_key[k](v)
        return kwargs

    return key_based_val_trans


def _mk(self, *args, **kwargs):
    """
    Make a full name with given kwargs. All required name=val must be present (or infered by self.process_kwargs
    function.
    The required fields are in self.fields.
    Does NOT check for validity of the vals.
    :param kwargs: The name=val arguments needed to construct a valid name
    :return: an name
    """
    n = len(args) + len(kwargs)
    if n > self.n_fields:
        raise ValueError(f"You have too many arguments: (args, kwargs) is ({args},{kwargs})")
    elif n < self.n_fields:
        raise ValueError(f"You have too few arguments: (args, kwargs) is ({args},{kwargs})")
    kwargs = dict({k: v for k, v in zip(self.fields, args)}, **kwargs)
    if self.process_kwargs is not None:
        kwargs = self.process_kwargs(**kwargs)
    return self.template.format(**kwargs)


class StrTupleDict(object):

    def __init__(self, template: (str, tuple, list), format_dict=None,
                 process_kwargs=None, process_info_dict=None,
                 named_tuple_type_name='NamedTuple',
                 sep: str = path_sep):
        """Converting from and to strings, tuples, and dicts.

        Args:
            template: The string format template
            format_dict: A {field_name: field_value_format_regex, ...} dict
            process_kwargs: A function taking the field=value pairs and producing a dict of processed
                {field: value,...} dict (where both fields and values could have been processed.
                This is useful when we need to process (format, default, etc.) fields, or their values,
                according to the other fields of values in the collection.
                A specification of {field: function_to_process_this_value,...} wouldn't allow the full powers
                we are allowing here.
            process_info_dict: A sort of converse of format_dict.
                This is a {field_name: field_conversion_func, ...} dict that is used to convert info_dict values
                before returning them.
            name_separator: Used

        >>> ln = StrTupleDict('/home/{user}/fav/{num}.txt',
        ...	                  format_dict={'user': '[^/]+', 'num': '\d+'},
        ...	                  process_info_dict={'num': int},
        ...                   sep='/'
        ...	                 )
        >>> ln.is_valid('/home/USER/fav/123.txt')
        True
        >>> ln.is_valid('/home/US/ER/fav/123.txt')
        False
        >>> ln.is_valid('/home/US/ER/fav/not_a_number.txt')
        False
        >>> ln.mk('USER', num=123)  # making a string (with args or kwargs)
        '/home/USER/fav/123.txt'
        >>> # Note: but ln.mk('USER', num='not_a_number') would fail because num is not valid
        >>> ln.info_dict('/home/USER/fav/123.txt')  # note in the output, 123 is an int, not a string
        {'user': 'USER', 'num': 123}
        >>>
        >>> # Trying with template given as a tuple, and with different separator
        >>> ln = StrTupleDict(template=('first', 'last', 'age'),
        ...                   format_dict={'age': '-*\d+'},
        ...                   process_info_dict={'age': int},
        ...                   sep=',')
        >>> ln.tuple_to_str(('Thor', "Odinson", 1500))
        'Thor,Odinson,1500'
        >>> ln.str_to_dict('Loki,Laufeyson,1070')
        {'first': 'Loki', 'last': 'Laufeyson', 'age': 1070}
        >>> ln.str_to_tuple('Odin,Himself,-1')
        ('Odin', 'Himself', -1)
        >>> ln.tuple_to_dict(('Odin', 'Himself', -1))
        {'first': 'Odin', 'last': 'Himself', 'age': -1}
        >>> ln.dict_to_tuple({'first': 'Odin', 'last': 'Himself', 'age': -1})
        ('Odin', 'Himself', -1)
        """
        if format_dict is None:
            format_dict = {}

        self.sep = sep

        if isinstance(template, str):
            self.template = template
        else:
            self.template = self.sep.join([f"{{{x}}}" for x in template])

        fields = get_fields_from_template(self.template)

        format_dict = mk_format_mapping_dict(format_dict, fields)

        named_capture_patterns = mk_named_capture_patterns(format_dict)

        pattern = template_to_pattern(named_capture_patterns, self.template)
        pattern += '$'
        pattern = re.compile(pattern)

        extract_pattern = {}
        for name in fields:
            extract_pattern[name] = mk_extract_pattern(self.template, format_dict, named_capture_patterns, name)

        if isinstance(process_info_dict, dict):
            _processor_for_kw = process_info_dict

            def process_info_dict(**info_dict):
                return {k: _processor_for_kw.get(k, lambda x: x)(v) for k, v in info_dict.items()}

        self.fields = fields
        self.n_fields = len(fields)
        self.format_dict = format_dict
        self.named_capture_patterns = named_capture_patterns
        self.pattern = pattern
        self.extract_pattern = extract_pattern
        self.process_kwargs = process_kwargs
        self.process_info_dict = process_info_dict

        def _mk(self, *args, **kwargs):
            """
            Make a full name with given kwargs. All required name=val must be present (or infered by self.process_kwargs
            function.
            The required fields are in self.fields.
            Does NOT check for validity of the vals.
            :param kwargs: The name=val arguments needed to construct a valid name
            :return: an name
            """
            n = len(args) + len(kwargs)
            if n > self.n_fields:
                raise ValueError(f"You have too many arguments: (args, kwargs) is ({args},{kwargs})")
            elif n < self.n_fields:
                raise ValueError(f"You have too few arguments: (args, kwargs) is ({args},{kwargs})")
            kwargs = dict({k: v for k, v in zip(self.fields, args)}, **kwargs)
            if self.process_kwargs is not None:
                kwargs = self.process_kwargs(**kwargs)
            return self.template.format(**kwargs)

        set_signature_of_func(_mk, ['self'] + self.fields)
        self.mk = MethodType(_mk, self)
        self.NamedTuple = namedtuple(named_tuple_type_name, self.fields)

    def is_valid(self, s: str):
        """Check if the name has the "upload format" (i.e. the kind of fields that are _ids of fv_mgc, and what
        name means in most of the iatis system.
        :param s: the string to check
        :return: True iff name has the upload format
        """
        return bool(self.pattern.match(s))

    def str_to_dict(self, s: str):
        """
        Get a dict with the arguments of an name (for example group, user, subuser, etc.)
        :param s:
        :return: a dict holding the argument fields and values
        """
        m = self.pattern.match(s)
        if m:
            info_dict = m.groupdict()
            if self.process_info_dict:
                return self.process_info_dict(**info_dict)
            else:
                return info_dict
        else:
            raise ValueError(f"Invalid string format: {s}")

    def str_to_tuple(self, s: str):
        info_dict = self.str_to_dict(s)
        return tuple(info_dict[x] for x in self.fields)

    def str_to_namedtuple(self, s: str):
        return self.dict_to_namedtuple(self.str_to_dict(s))

    def super_dict_to_str(self, d: dict):
        """Like dict_to_str, but the input dict can have extra keys that are not used by dict_to_str"""
        return self.mk(**{k: v for k, v in d.items() if k in self.fields})

    def dict_to_str(self, d: dict):
        return self.mk(**d)

    def dict_to_tuple(self, d):
        assert_condition(len(self.fields) == len(d), f"len(d)={len(d)} but len(fields)={len(self.fields)}")
        return tuple(d[f] for f in self.fields)

    def dict_to_namedtuple(self, d):
        return self.NamedTuple(**d)

    def tuple_to_dict(self, t):
        assert_condition(len(self.fields) == len(t), f"len(d)={len(t)} but len(fields)={len(self.fields)}")
        return {f: x for f, x in zip(self.fields, t)}

    def tuple_to_str(self, t):
        return self.mk(*t)

    def namedtuple_to_tuple(self, nt):
        return tuple(nt)

    def namedtuple_to_dict(self, nt):
        return {k: getattr(nt, k) for k in self.fields}

    def namedtuple_to_str(self, nt):
        return self.dict_to_str(self.namedtuple_to_dict(nt))

    def extract(self, field, s):
        """Extract a single item from an name
        :param field: field of the item to extract
        :param s: the string from which to extract it
        :return: the value for name
        """
        return self.extract_pattern[field].match(s).group(1)

    info_dict = str_to_dict  # alias
    info_tuple = str_to_tuple  # alias

    def replace_name_elements(self, s: str, **elements_kwargs):
        """Replace specific name argument values with others
        :param s: the string to replace
        :param elements_kwargs: the arguments to replace (and their values)
        :return: a new name
        """
        name_info_dict = self.info_dict(s)
        for k, v in elements_kwargs.items():
            name_info_dict[k] = v
        return self.mk(**name_info_dict)

    def _info_str(self):
        kv = self.__dict__.copy()
        exclude = ['process_kwargs', 'extract_pattern', 'prefix_pattern',
                   'prefix_template_including_name', 'prefix_template_excluding_name']
        for f in exclude:
            kv.pop(f)
        s = ""
        s += "  * {}: {}\n".format('template', kv.pop('template'))
        s += "  * {}: {}\n".format('template', kv.pop('sep'))
        s += "  * {}: {}\n".format('format_dict', kv.pop('format_dict'))

        for k, v in kv.items():
            if hasattr(v, 'pattern'):
                v = v.pattern
            s += "  * {}: {}\n".format(k, v)

        return s

    def _print_info_str(self):
        print(self._info_str())


# TODO: mk_prefix has wrong signature. Repair.
class StrTupleDictWithPrefix(StrTupleDict):
    """Converting from and to strings, tuples, and dicts, but with partial "prefix" specs allowed.

    Args:
        template: The string format template
        format_dict: A {field_name: field_value_format_regex, ...} dict
        process_kwargs: A function taking the field=value pairs and producing a dict of processed
            {field: value,...} dict (where both fields and values could have been processed.
            This is useful when we need to process (format, default, etc.) fields, or their values,
            according to the other fields of values in the collection.
            A specification of {field: function_to_process_this_value,...} wouldn't allow the full powers
            we are allowing here.
        process_info_dict: A sort of converse of format_dict.
            This is a {field_name: field_conversion_func, ...} dict that is used to convert info_dict values
            before returning them.
        name_separator: Used

    >>> ln = StrTupleDictWithPrefix('/home/{user}/fav/{num}.txt',
    ...	                  format_dict={'user': '[^/]+', 'num': '\d+'},
    ...	                  process_info_dict={'num': int},
    ...                   sep='/'
    ...	                 )
    >>> ln.mk('USER', num=123)  # making a string (with args or kwargs)
    '/home/USER/fav/123.txt'
    >>> ####### prefix methods #######
    >>> ln.is_valid_prefix('/home/USER/fav/')
    True
    >>> ln.is_valid_prefix('/home/USER/fav/12')  # False because too long
    False
    >>> ln.is_valid_prefix('/home/USER/fav')  # False because too short
    False
    >>> ln.is_valid_prefix('/home/')  # True because just right
    True
    >>> ln.is_valid_prefix('/home/USER/fav/123.txt')  # full path, so output same as is_valid() method
    True
    >>>
    >>> ln.mk_prefix('ME')
    '/home/ME/fav/'
    >>> ln.mk_prefix(user='YOU', num=456)  # full specification, so output same as same as mk() method
    '/home/YOU/fav/456.txt'
    """

    @wraps(StrTupleDict.__init__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prefix_template_including_name, self.prefix_template_excluding_name = \
            mk_prefix_templates_dicts(self.template)

        _prefix_pattern = '$|'.join(
            [x.format(**self.format_dict) for x in sorted(list(self.prefix_template_including_name.values()), key=len)])
        _prefix_pattern += '$'
        self.prefix_pattern = re.compile(_prefix_pattern)

        def _mk_prefix(self, *args, **kwargs):
            """
            Make a prefix for an uploads name that has has the path up to the first None argument.
            :return: A string that is the prefix of a valid name
            """
            assert len(args) + len(kwargs) <= self.n_fields, "You have too many arguments"
            kwargs = dict({k: v for k, v in zip(self.fields, args)}, **kwargs)
            if self.process_kwargs is not None:
                kwargs = self.process_kwargs(**kwargs)

            # ascertain that no fields were skipped (we can leave fields out at the end, but not in the middle)
            a_name_was_skipped = False
            for name in self.fields:
                if name not in kwargs:
                    if a_name_was_skipped == True:
                        raise ValueError("You are making a PREFIX: This means you can't skip any fields. "
                                         "Once a name is omitted, you need to omit all further fields. "
                                         f"The name order is {self.fields}. You specified {tuple(kwargs.keys())}")
                    else:
                        a_name_was_skipped = True

            keep_kwargs = {}
            last_name = None
            for name in self.fields:
                if name in kwargs:
                    keep_kwargs[name] = kwargs[name]
                    last_name = name
                else:
                    break

            return self.prefix_template_including_name[last_name].format(**keep_kwargs)

        set_signature_of_func(_mk_prefix, [(s, None) for s in self.fields])
        self.mk_prefix = MethodType(_mk_prefix, self)

    def is_valid_prefix(self, s):
        """Check if name is a valid prefix.
        :param s: a string (that might or might not be a valid prefix)
        :return: True iff name is a valid prefix
        """
        return bool(self.prefix_pattern.match(s))


LinearNaming = StrTupleDictWithPrefix

from py2store.base import Store
from collections import namedtuple
from py2store.util import lazyprop


class ParametricKeyStore(Store):
    def __init__(self, store, keymap=None):
        super().__init__(store)
        self._keymap = keymap

    @property
    def _linear_naming(self):
        print("_linear_naming Deprecated: Use _keymap instead")
        return self._keymap


class StoreWithTupleKeys(ParametricKeyStore):
    def _id_of_key(self, key):
        return self._keymap.mk(*key)

    def _key_of_id(self, _id):
        return self._keymap.info_tuple(_id)


class StoreWithDictKeys(ParametricKeyStore):
    def _id_of_key(self, key):
        return self._keymap.mk(**key)

    def _key_of_id(self, _id):
        return self._keymap.info_dict(_id)


class StoreWithNamedTupleKeys(ParametricKeyStore):
    @lazyprop
    def NamedTupleKey(self):
        return namedtuple('NamedTupleKey', field_names=self._keymap.fields)

    def _id_of_key(self, key):
        return self._keymap.mk(*key)

    def _key_of_id(self, _id):
        return self.NamedTupleKey(*self._keymap.info_tuple(_id))


# def mk_parametric_key_store_cls(store_cls, key_type=tuple):
#     if key_type == tuple:
#         super_cls = StoreWithTupleKeys
#     elif key_type == dict:
#         super_cls = StoreWithDictKeys
#     else:
#         raise ValueError("key_type needs to be tuple or dict")
#
#     class A(super_cls, store_cls):
#         def __init__(self, rootdir, subpath='', format_dict=None, process_kwargs=None, process_info_dict=None,
#                      **extra_store_kwargs):
#
#             path_format = os.path.join(rootdir, subpath)
#             store = store_cls.__init__(self, path_format=path_format, **extra_store_kwargs)
#             linear_naming = LinearNaming()
#
#             # FilepathFormatKeys.__init__(self, path_format)


class NamingInterface:
    def __init__(self,
                 params=None,
                 validation_funs=None,
                 all_kwargs_should_be_in_validation_dict=dflt_all_kwargs_should_be_in_validation_dict,
                 ignore_misunderstood_validation_instructions=dflt_ignore_misunderstood_validation_instructions,
                 **kwargs):
        if params is None:
            params = {}
        if validation_funs is None:
            validation_funs = dflt_validation_funs
        validation_dict = {var: info.get('validation', {}) for var, info in params.items()}
        default_dict = {var: info.get('default', None) for var, info in params.items()}
        arg_pattern = {var: info.get('arg_pattern', dflt_arg_pattern) for var, info in params.items()}
        named_arg_pattern = {var: '(?P<' + var + '>' + pat + ')' for var, pat in arg_pattern.items()}
        to_str = {var: info['to_str'] for var, info in params.items() if 'to_str' in info}
        to_val = {var: info['to_val'] for var, info in params.items() if 'to_val' in info}

        self.validation_dict = validation_dict
        self.default_dict = default_dict
        self.arg_pattern = arg_pattern
        self.named_arg_pattern = named_arg_pattern
        self.to_str = to_str
        self.to_val = to_val

        self.validation_funs = validation_funs
        self.all_kwargs_should_be_in_validation_dict = all_kwargs_should_be_in_validation_dict
        self.ignore_misunderstood_validation_instructions = ignore_misunderstood_validation_instructions

    def validate_kwargs(self, **kwargs):
        return validate_kwargs(kwargs_to_validate=kwargs,
                               validation_dict=self.validation_dict,
                               validation_funs=self.validation_funs,
                               all_kwargs_should_be_in_validation_dict=self.all_kwargs_should_be_in_validation_dict,
                               ignore_misunderstood_validation_instructions=self.ignore_misunderstood_validation_instructions)

    def default_for(self, arg, **kwargs):
        default = self.default_dict[arg]
        if not isinstance(default, dict) or 'args' not in default or 'func' not in default:
            return default
        else:  # call the func on the default['args'] values given in kwargs
            args = {arg_: kwargs[arg_] for arg_ in default['args']}
            return default['func'](*args)

    def str_kwargs_from(self, **kwargs):
        return {k: self.to_str[k](v) for k, v in kwargs.items() if k in self.to_str}

    def val_kwargs_from(self, **kwargs):
        return {k: self.to_val[k](v) for k, v in kwargs.items() if k in self.to_val}

    def name_for(self, **kwargs):
        raise NotImplementedError("Interface method: Method needs to be implemented")

    def info_for(self, **kwargs):
        raise NotImplementedError("Interface method: Method needs to be implemented")

    def is_valid_name(self, name):
        raise NotImplementedError("Interface method: Method needs to be implemented")


class BigDocTest():
    """
    >>>
    >>> e_name = BigDocTest.mk_e_naming()
    >>> u_name = BigDocTest.mk_u_naming()
    >>> e_sref = 's3://bucket-GROUP/example/files/USER/SUBUSER/2017-01-24/1485272231982_1485261448469'
    >>> u_sref = "s3://uploads/GROUP/upload/files/USER/2017-01-24/SUBUSER/a_file.wav"
    >>> u_name_2 = "s3://uploads/ANOTHER_GROUP/upload/files/ANOTHER_USER/2017-01-24/SUBUSER/a_file.wav"
    >>>
    >>> ####### is_valid(self, name): ######
    >>> e_name.is_valid(e_sref)
    True
    >>> e_name.is_valid(u_sref)
    False
    >>> u_name.is_valid(u_sref)
    True
    >>>
    >>> ####### is_valid_prefix(self, name): ######
    >>> e_name.is_valid_prefix('s3://bucket-')
    True
    >>> e_name.is_valid_prefix('s3://bucket-GROUP')
    False
    >>> e_name.is_valid_prefix('s3://bucket-GROUP/example/')
    False
    >>> e_name.is_valid_prefix('s3://bucket-GROUP/example/files')
    False
    >>> e_name.is_valid_prefix('s3://bucket-GROUP/example/files/')
    True
    >>> e_name.is_valid_prefix('s3://bucket-GROUP/example/files/USER/SUBUSER/2017-01-24/')
    True
    >>> e_name.is_valid_prefix('s3://bucket-GROUP/example/files/USER/SUBUSER/2017-01-24/0_0')
    True
    >>>
    >>> ####### info_dict(self, name): ######
    >>> e_name.info_dict(e_sref)  # see that utc_ms args were cast to ints
    {'group': 'GROUP', 'user': 'USER', 'subuser': 'SUBUSER', 'day': '2017-01-24', 's_ums': 1485272231982, 'e_ums': 1485261448469}
    >>> u_name.info_dict(u_sref)  # returns None (because self was made for example!
    {'group': 'GROUP', 'user': 'USER', 'day': '2017-01-24', 'subuser': 'SUBUSER', 'filename': 'a_file.wav'}
    >>> # but with a u_name, it will work
    >>> u_name.info_dict(u_sref)
    {'group': 'GROUP', 'user': 'USER', 'day': '2017-01-24', 'subuser': 'SUBUSER', 'filename': 'a_file.wav'}
    >>>
    >>> ####### extract(self, item, name): ######
    >>> e_name.extract('group', e_sref)
    'GROUP'
    >>> e_name.extract('user', e_sref)
    'USER'
    >>> u_name.extract('group', u_name_2)
    'ANOTHER_GROUP'
    >>> u_name.extract('user', u_name_2)
    'ANOTHER_USER'
    >>>
    >>> ####### mk_prefix(self, *args, **kwargs): ######
    >>> e_name.mk_prefix()
    's3://bucket-'
    >>> e_name.mk_prefix(group='GROUP')
    's3://bucket-GROUP/example/files/'
    >>> e_name.mk_prefix(group='GROUP', user='USER')
    's3://bucket-GROUP/example/files/USER/'
    >>> e_name.mk_prefix(group='GROUP', user='USER', subuser='SUBUSER')
    's3://bucket-GROUP/example/files/USER/SUBUSER/'
    >>> e_name.mk_prefix(group='GROUP', user='USER', subuser='SUBUSER', day='0000-00-00')
    's3://bucket-GROUP/example/files/USER/SUBUSER/0000-00-00/'
    >>> e_name.mk_prefix(group='GROUP', user='USER', subuser='SUBUSER', day='0000-00-00',
    ... s_ums=1485272231982)
    's3://bucket-GROUP/example/files/USER/SUBUSER/0000-00-00/1485272231982_'
    >>> e_name.mk_prefix(group='GROUP', user='USER', subuser='SUBUSER', day='0000-00-00',
    ... s_ums=1485272231982, e_ums=1485261448469)
    's3://bucket-GROUP/example/files/USER/SUBUSER/0000-00-00/1485272231982_1485261448469'
    >>>
    >>> u_name.mk_prefix()
    's3://uploads/'
    >>> u_name.mk_prefix(group='GROUP')
    's3://uploads/GROUP/upload/files/'
    >>> u_name.mk_prefix(group='GROUP', user='USER')
    's3://uploads/GROUP/upload/files/USER/'
    >>> u_name.mk_prefix(group='GROUP', user='USER', day='DAY')
    's3://uploads/GROUP/upload/files/USER/DAY/'
    >>> u_name.mk_prefix(group='GROUP', user='USER', day='DAY')
    's3://uploads/GROUP/upload/files/USER/DAY/'
    >>> u_name.mk_prefix(group='GROUP', user='USER', day='DAY', subuser='SUBUSER')
    's3://uploads/GROUP/upload/files/USER/DAY/SUBUSER/'
    >>>
    >>> ####### mk(self, *args, **kwargs): ######
    >>> e_name.mk(group='GROUP', user='USER', subuser='SUBUSER', day='0000-00-00',
    ...             s_ums=1485272231982, e_ums=1485261448469)
    's3://bucket-GROUP/example/files/USER/SUBUSER/0000-00-00/1485272231982_1485261448469'
    >>> e_name.mk(group='GROUP', user='USER', subuser='SUBUSER', day='from_s_ums',
    ...             s_ums=1485272231982, e_ums=1485261448469)
    's3://bucket-GROUP/example/files/USER/SUBUSER/2017-01-24/1485272231982_1485261448469'
    >>>
    >>> ####### replace_name_elements(self, *args, **kwargs): ######
    >>> name = 's3://bucket-redrum/example/files/oopsy@domain.com/ozeip/2008-11-04/1225779243969_1225779246969'
    >>> e_name.replace_name_elements(name, user='NEW_USER', group='NEW_GROUP')
    's3://bucket-NEW_GROUP/example/files/NEW_USER/ozeip/2008-11-04/1225779243969_1225779246969'
    """

    @staticmethod
    def process_info_dict_for_example(**info_dict):
        if 's_ums' in info_dict:
            info_dict['s_ums'] = int(info_dict['s_ums'])
        if 'e_ums' in info_dict:
            info_dict['e_ums'] = int(info_dict['e_ums'])
        return info_dict

    @staticmethod
    def example_process_kwargs(**kwargs):
        from datetime import datetime
        epoch = datetime.utcfromtimestamp(0)
        second_ms = 1000.0

        def utcnow_ms():
            return (datetime.utcnow() - epoch).total_seconds() * second_ms

        # from ut.util.time import second_ms, utcnow_ms
        if 's_ums' in kwargs:
            kwargs['s_ums'] = int(kwargs['s_ums'])
        if 'e_ums' in kwargs:
            kwargs['e_ums'] = int(kwargs['e_ums'])

        if 'day' in kwargs:
            day = kwargs['day']
            # get the day in the expected format
            if isinstance(day, str):
                if day == 'now':
                    day = datetime.utcfromtimestamp(int(utcnow_ms() / second_ms)).strftime(day_format)
                elif day == 'from_s_ums':
                    assert 's_ums' in kwargs, "need to have s_ums argument"
                    day = datetime.utcfromtimestamp(int(kwargs['s_ums'] / second_ms)).strftime(day_format)
                else:
                    assert day_format_pattern.match(day)
            elif isinstance(day, datetime):
                day = day.strftime(day_format)
            elif 's_ums' in kwargs:  # if day is neither a string nor a datetime
                day = datetime.utcfromtimestamp(int(kwargs['s_ums'] / second_ms)).strftime(day_format)

            kwargs['day'] = day

        return kwargs

    @staticmethod
    def mk_e_naming():
        return LinearNaming(
            template='s3://bucket-{group}/example/files/{user}/{subuser}/{day}/{s_ums}_{e_ums}',
            format_dict={'s_ums': '\d+', 'e_ums': '\d+', 'day': "[^/]+"},
            process_kwargs=BigDocTest.example_process_kwargs,
            process_info_dict=BigDocTest.process_info_dict_for_example
        )

    @staticmethod
    def mk_u_naming():
        return LinearNaming(
            template='s3://uploads/{group}/upload/files/{user}/{day}/{subuser}/{filename}',
            format_dict={'day': "[^/]+", 'filepath': '.+'}
        )


import os
from functools import wraps
from py2store.trans import wrap_kvs

pjoin = os.path.join

KeyMapNames = namedtuple('KeyMaps', ['key_of_id', 'id_of_key'])
KeyMaps = namedtuple('KeyMaps', ['key_of_id', 'id_of_key'])


def _get_keymap_names_for_str_to_key_type(key_type):
    if not isinstance(key_type, str):
        key_type = {tuple: 'tuple', namedtuple: 'namedtuple', dict: 'dict', str: 'str'}.get(key_type, None)

    if key_type not in {'tuple', 'namedtuple', 'dict', 'str'}:
        raise ValueError(f"Not a recognized key_type: {key_type}")

    return KeyMapNames(key_of_id=f"str_to_{key_type}", id_of_key=f"{key_type}_to_str")


def _get_method_for_str_to_key_type(keymap, key_type):
    kmn = _get_keymap_names_for_str_to_key_type(key_type)
    return KeyMaps(key_of_id=getattr(keymap, kmn.key_of_id),
                   id_of_key=getattr(keymap, kmn.id_of_key))


def mk_store_from_path_format_store_cls(store, subpath='', store_cls_kwargs=None,
                                        key_type=namedtuple,
                                        keymap=StrTupleDict, keymap_kwargs=None,
                                        name=None):
    """Wrap a store (instance or class) that uses string keys to make it into a store that uses a specific key format.

    Args:
        store: The instance or class to wrap
        subpath: The subpath (defining the subset of the data pointed at by the URI
        store_cls_kwargs:  # if store is a class, the kwargs that you would have given the store_cls to make itself
        key_type: The key type you want to interface with:
            dict, tuple, namedtuple, str or 'dict', 'tuple', 'namedtuple', 'str'
        keymap:  # the keymap instance or class you want to use to map keys
        keymap_kwargs:  # if keymap is a cls, the kwargs to give it (besides the subpath)
        name: The name to give the class the function will make here

    Returns: An instance of a wrapped class


    Example:
    ```
    # Get a (sessiono,bt) indexed LocalJsonStore
    s = mk_store_from_path_format_store_cls(LocalJsonStore,
                                                   os.path.join(root_dir, 'd'),
                                                   subpath='{session}/d/{bt}',
                                                   keymap_kwargs=dict(process_info_dict={'session': int, 'bt': int}))
    ```
    """
    if isinstance(keymap, type):
        keymap = keymap(subpath, **(keymap_kwargs or {}))  # make the keymap instance

    km = _get_method_for_str_to_key_type(keymap, key_type)

    if isinstance(store, type):
        name = name or 'KeyWrapped' + store.__name__
        _WrappedStoreCls = wrap_kvs(store, name=name,
                                    key_of_id=km.key_of_id, id_of_key=km.id_of_key)

        class WrappedStoreCls(_WrappedStoreCls):
            def __init__(self, root_uri):
                path_format = pjoin(root_uri, subpath)
                super().__init__(path_format, **(store_cls_kwargs or {}))

        return WrappedStoreCls
    else:
        name = name or 'KeyWrapped' + store.__class__.__name__
        return wrap_kvs(store, name=name, key_of_id=km.key_of_id, id_of_key=km.id_of_key)


mk_tupled_store_from_path_format_store_cls = mk_store_from_path_format_store_cls
