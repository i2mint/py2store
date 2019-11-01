"""
This module is about generating, validating, and operating on (parametrized) names (i.e. stings, e.g. paths).
"""

import re

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

until_slash = "[^/]+"
until_slash_capture = '(' + until_slash + ')'

capture_template = '({format})'
named_capture_template = '(?P<{name}>{format})'

names_re = re.compile('(?<={)[^}]+(?=})')


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


def get_names_from_template(template):
    """
    Get list from {item} items of template string
    :param template: a "template" string (a string with {item} items
    -- the kind that is used to mark token for str.format)
    :return: a list of the token items of the string, in the order they appear
    >>> get_names_from_template('this{is}an{example}of{a}template')
    ['is', 'example', 'a']
    """
    return names_re.findall(template)


def mk_format_mapping_dict(format_dict, required_keys, default_format=until_slash):
    new_format_dict = format_dict.copy()
    for k in required_keys:
        if k not in new_format_dict:
            new_format_dict[k] = default_format
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
    p = re.compile("{}".format("|".join(['{' + re.escape(x) + '}' for x in list(mapping_dict.keys())])))
    return p.sub(lambda x: mapping_dict[x.string[(x.start() + 1):(x.end() - 1)]], template)


def mk_extract_pattern(template, format_dict, named_capture_patterns, name):
    mapping_dict = dict(format_dict, **{name: named_capture_patterns[name]})
    p = re.compile("{}".format("|".join(
        ['{' + re.escape(x) + '}' for x in list(mapping_dict.keys())])))

    return re.compile(p.sub(lambda x: mapping_dict[x.string[(x.start() + 1):(x.end() - 1)]], template))


def mk_prefix_templates_dicts(template):
    names = get_names_from_template(template)
    prefix_template_dict_including_name = dict()
    none_and_names = [None] + names
    for name in none_and_names:
        if name == names[-1]:
            prefix_template_dict_including_name[name] = template
        else:
            if name is None:
                next_name = names[0]
            else:
                next_name = names[1 + next(i for i, _name in enumerate(names) if _name == name)]
            p = '{' + next_name + '}'
            template_idx_of_next_name = re.search(p, template).start()
            prefix_template_dict_including_name[name] = template[:template_idx_of_next_name]

    prefix_template_dict_excluding_name = dict()
    for i, name in enumerate(names):
        prefix_template_dict_excluding_name[name] = prefix_template_dict_including_name[none_and_names[i]]
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


class LinearNaming(object):
    def __init__(self, template, format_dict=None,
                 process_kwargs=None, process_info_dict=None):
        """

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

        >>> ln = LinearNaming('/home/{user}/fav/{num}.txt',
        ...	                  format_dict={'user': '[^/]+', 'num': '\d+'},
        ...	                  process_info_dict={'num': int}
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
        >>> ####### prefix methods #######
        >>> ln.is_valid_prefix('/home/USER/fav/')
        True
        >>> ln.is_valid_prefix('/home/USER/fav/12')
        False  # too long
        >>> ln.is_valid_prefix('/home/USER/fav')
        False  # too short
        >>> ln.is_valid_prefix('/home/')
        True  # just right
        >>> ln.is_valid_prefix('/home/USER/fav/123.txt')  # full path, so output same as is_valid() method
        True
        >>>
        >>> ln.mk_prefix('ME')
        '/home/ME/fav/'
        >>> ln.mk_prefix(user='YOU', num=456)  # full specification, so output same as same as mk() method
        '/home/YOU/fav/456.txt'
        """
        if format_dict is None:
            format_dict = {}

        self.template = template

        names = get_names_from_template(template)

        format_dict = mk_format_mapping_dict(format_dict, names)

        named_capture_patterns = mk_named_capture_patterns(format_dict)

        pattern = template_to_pattern(named_capture_patterns, template)
        pattern += '$'
        pattern = re.compile(pattern)

        extract_pattern = {}
        for name in names:
            extract_pattern[name] = mk_extract_pattern(template, format_dict, named_capture_patterns, name)

        if isinstance(process_info_dict, dict):
            _processor_for_kw = process_info_dict

            def process_info_dict(**info_dict):
                return {k: _processor_for_kw.get(k, lambda x: x)(v) for k, v in info_dict.items()}

        self.names = names
        self.n_names = len(names)
        self.format_dict = format_dict
        self.named_capture_patterns = named_capture_patterns
        self.pattern = pattern
        self.extract_pattern = extract_pattern
        self.process_kwargs = process_kwargs
        self.process_info_dict = process_info_dict

        self.prefix_template_including_name, self.prefix_template_excluding_name = \
            mk_prefix_templates_dicts(self.template)

        _prefix_pattern = '$|'.join(
            [x.format(**self.format_dict) for x in sorted(list(self.prefix_template_including_name.values()), key=len)])
        _prefix_pattern += '$'
        self.prefix_pattern = re.compile(_prefix_pattern)

    def __call__(self, *args, **kwargs):
        return self.mk(*args, **kwargs)

    def is_valid(self, sref):
        """
        Check if the name has the "upload format" (i.e. the kind of srefs that are _ids of fv_mgc, and what
        sref means in most of the iatis system.
        :param sref: the sref (string) to check
        :return: True iff sref has the upload format
        """
        return bool(self.pattern.match(sref))

    def is_valid_prefix(self, sref):
        """
        Check if sref is a valid prefix.
        :param sref: a string (that might be a valid sref prefix)
        :return: True iff sref is a valid prefix
        """
        return bool(self.prefix_pattern.match(sref))

    def info_dict(self, sref):
        """
        Get a dict with the arguments of an sref (for example group, user, subuser, etc.)
        :param sref:
        :return: a dict holding the argument names and values
        """
        m = self.pattern.match(sref)
        if m:
            info_dict = m.groupdict()
            if self.process_info_dict:
                return self.process_info_dict(**info_dict)
            else:
                return info_dict

    def info_tuple(self, sref):
        info_dict = self.info_dict(sref)
        return tuple(info_dict[x] for x in self.names)

    def extract(self, item, sref):
        """
        Extract a single item from an sref
        :param item: item of the item to extract
        :param sref: the sref from which to extract it
        :return: the value for name
        """
        return self.extract_pattern[item].match(sref).group(1)

    def mk_prefix(self, *args, **kwargs):
        """
        Make a prefix for an uploads sref that has has the path up to the first None argument.
        :return: A string that is the prefix of a valid sref
        """
        assert len(args) + len(kwargs) <= self.n_names, "You have too many arguments"
        kwargs = dict({k: v for k, v in zip(self.names, args)}, **kwargs)
        if self.process_kwargs is not None:
            kwargs = self.process_kwargs(**kwargs)

        keep_kwargs = {}
        last_name = None
        for name in self.names:
            if name in kwargs:
                keep_kwargs[name] = kwargs[name]
                last_name = name
            else:
                break

        return self.prefix_template_including_name[last_name].format(**keep_kwargs)

    def mk(self, *args, **kwargs):
        """
        Make a full sref with given kwargs. All required name=val must be present (or infered by self.process_kwargs
        function.
        The required names are in self.names.
        Does NOT check for validity of the vals.
        :param kwargs: The name=val arguments needed to construct a valid sref
        :return: an sref
        """
        assert len(args) + len(kwargs) == self.n_names, "You're missing, or have too many arguments"
        kwargs = dict({k: v for k, v in zip(self.names, args)}, **kwargs)
        if self.process_kwargs is not None:
            kwargs = self.process_kwargs(**kwargs)
        return self.template.format(**kwargs)

    def replace_sref_elements(self, sref, **elements_kwargs):
        """
        Replace specific sref argument values with others
        :param sref: the sref to replace
        :param elements_kwargs: the arguments to replace (and their values)
        :return: a new sref
        """
        sref_info_dict = self.info_dict(sref)
        for k, v in elements_kwargs.items():
            sref_info_dict[k] = v
        return self.mk(**sref_info_dict)

    def __repr__(self):
        kv = self.__dict__.copy()
        exclude = ['process_kwargs', 'extract_pattern', 'prefix_pattern',
                   'prefix_template_including_name', 'prefix_template_excluding_name']
        for f in exclude:
            kv.pop(f)
        s = ""
        s += "  * {}: {}\n\n".format('template', kv.pop('template'))
        s += "  * {}: {}\n\n".format('format_dict', kv.pop('format_dict'))

        for k, v in kv.items():
            if hasattr(v, 'pattern'):
                v = v.pattern
            s += "  * {}: {}\n\n".format(k, v)
        return s


from py2store.base import Store


class StoreWithTupleKeys(Store):
    def __init__(self, store, linear_naming=None):
        super().__init__(store)
        self._linear_naming = linear_naming

    def _id_of_key(self, key):
        return self._linear_naming.mk(*key)

    def _key_of_id(self, _id):
        return self._linear_naming.info_tuple(_id)


class StoreWithDictKeys(Store):
    def __init__(self, store, linear_naming=None):
        super().__init__(store)
        self._linear_naming = linear_naming

    def _id_of_key(self, key):
        return self._linear_naming.mk(**key)

    def _key_of_id(self, _id):
        return self._linear_naming.info_dict(_id)


class NamingInterface(object):
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
    >>> u_sref_2 = "s3://uploads/ANOTHER_GROUP/upload/files/ANOTHER_USER/2017-01-24/SUBUSER/a_file.wav"
    >>>
    >>> ####### is_valid(self, sref): ######
    >>> e_name.is_valid(e_sref)
    True
    >>> e_name.is_valid(u_sref)
    False
    >>> u_name.is_valid(u_sref)
    True
    >>>
    >>> ####### is_valid_prefix(self, sref): ######
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
    >>> ####### info_dict(self, sref): ######
    >>> e_name.info_dict(e_sref)  # see that utc_ms args were cast to ints
    {'group': 'GROUP', 'user': 'USER', 'subuser': 'SUBUSER', 'day': '2017-01-24', 's_ums': 1485272231982, 'e_ums': 1485261448469}
    >>> u_name.info_dict(u_sref)  # returns None (because self was made for example!
    {'group': 'GROUP', 'user': 'USER', 'day': '2017-01-24', 'subuser': 'SUBUSER', 'filename': 'a_file.wav'}
    >>> # but with a u_name, it will work
    >>> u_name.info_dict(u_sref)
    {'group': 'GROUP', 'user': 'USER', 'day': '2017-01-24', 'subuser': 'SUBUSER', 'filename': 'a_file.wav'}
    >>>
    >>> ####### extract(self, item, sref): ######
    >>> e_name.extract('group', e_sref)
    'GROUP'
    >>> e_name.extract('user', e_sref)
    'USER'
    >>> u_name.extract('group', u_sref_2)
    'ANOTHER_GROUP'
    >>> u_name.extract('user', u_sref_2)
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
    >>> ####### replace_sref_elements(self, *args, **kwargs): ######
    >>> sref = 's3://bucket-redrum/example/files/oopsy@domain.com/ozeip/2008-11-04/1225779243969_1225779246969'
    >>> e_name.replace_sref_elements(sref, user='NEW_USER', group='NEW_GROUP')
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
        from ut.util.time import second_ms, utcnow_ms
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
