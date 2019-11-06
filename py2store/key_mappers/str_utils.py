import string

dflt_formatter = string.Formatter()


def compile_str_from_parsed(parsed):
    """The (quasi-)inverse of string.Formatter.parse.

    Args:
        parsed: iterator of (literal_text, field_name, format_spec, conversion) tuples,
        as yield by string.Formatter.parse

    Returns:
        A format string that would produce such a parsed input.

    >>> s =  "ROOT/{}/{0!r}/{1!i:format}/hello{:0.02f}TAIL"
    >>> assert compile_str_from_parsed(string.Formatter().parse(s)) == s
    >>>
    >>> # Or, if you want to see more details...
    >>> parsed = list(string.Formatter().parse(s))
    >>> for p in parsed:
    ...     print(p)
    ('ROOT/', '', '', None)
    ('/', '0', '', 'r')
    ('/', '1', 'format', 'i')
    ('/hello', '', '0.02f', None)
    ('TAIL', None, None, None)
    >>> compile_str_from_parsed(parsed)
    'ROOT/{}/{0!r}/{1!i:format}/hello{:0.02f}TAIL'
    """
    result = ''
    for literal_text, field_name, format_spec, conversion in parsed:
        # output the literal text
        if literal_text:
            result += literal_text

        # if there's a field, output it
        if field_name is not None:
            result += '{'
            if field_name != '':
                result += field_name
            if conversion:
                result += '!' + conversion
            if format_spec:
                result += ':' + format_spec
            result += '}'
    return result


def transform_format_str(format_str, parsed_tuple_trans_func):
    return compile_str_from_parsed(
        map(lambda args: parsed_tuple_trans_func(*args), dflt_formatter.parse(format_str)))


def _empty_field_name(literal_text, field_name, format_spec, conversion):
    if field_name is not None:
        return literal_text, '', format_spec, conversion
    else:
        return literal_text, field_name, format_spec, conversion


def auto_field_format_str(format_str):
    """Get an auto field version of the format_str

    Args:
        format_str: A format string

    Returns:
        A transformed format_str that has no names {inside} {formatting} {braces}.
    >>> auto_field_format_str('R/{0}/{one}/{}/{two}/T')
    'R/{}/{}/{}/{}/T'
    """
    return transform_format_str(format_str, _empty_field_name)


def manual_field_format_str(format_str):
    """Get an auto field version of the format_str

    Args:
        format_str: A format string

    Returns:
        A transformed format_str that has no names {inside} {formatting} {braces}.
    >>> auto_field_format_str('R/{0}/{one}/{}/{two}/T')
    'R/{}/{}/{}/{}/T'
    """
    return transform_format_str(format_str, _empty_field_name)


def _mk_naming_trans_func(names=None):
    if names is None:
        names = map(str, range(99999))
    _names = iter(names)

    def trans_func(literal_text, field_name, format_spec, conversion):
        if field_name is not None:
            return literal_text, next(_names), format_spec, conversion
        else:
            return literal_text, field_name, format_spec, conversion

    return trans_func


def name_fields_in_format_str(format_str, field_names=None):
    """Get a manual field version of the format_str

    Args:
        format_str: A format string
        names: An iterable that produces enough strings to fill all of format_str fields

    Returns:
        A transformed format_str
    >>> name_fields_in_format_str('R/{0}/{one}/{}/{two}/T')
    'R/{0}/{1}/{2}/{3}/T'
    >>> # Note here that we use the field name to inject a field format as well
    >>> name_fields_in_format_str('R/{foo}/{0}/{}/T', ['42', 'hi:03.0f', 'world'])
    'R/{42}/{hi:03.0f}/{world}/T'
    """
    return transform_format_str(format_str, _mk_naming_trans_func(field_names))


no_hybrid_format_error = ValueError("cannot switch from manual field specification (i.e. {{number}} or {{name}}) "
                                    "to automatic (i.e. {{}}) field numbering.")


def _is_not_none(x):
    return x is not None


def format_params_in_str_format(format_string):
    """
    Get the "parameter" indices/names of the format_string

    Args:
        format_string: A format string (i.e. a string with {...} to mark parameter placement and formatting

    Returns:
        A list of parameter indices used in the format string, in the order they appear, with repetition.
        Parameter indices could be integers, strings, or None (to denote "automatic field numbering".
    >>> format_string = '{0} (no 1) {2}, and {0} is a duplicate, {} is unnamed and {name} is string-named'
    >>> format_params_in_str_format(format_string)
    [0, 2, 0, None, 'name']
    """
    return list(map(lambda x: int(x) if str.isnumeric(x) else x if x != '' else None,
                    filter(_is_not_none, (x[1] for x in dflt_formatter.parse(format_string)))))


def n_format_params_in_str_format(format_string):
    """ The number of parameters"""
    return len(set(format_params_in_str_format(format_string)))


def is_manual_format_string(format_string):
    """ Says if the format_string uses a manual specification
    See Also: is_automatic_format_string and
    >>> is_manual_format_string('Manual: indices: {1} {2}, named: {named} {fields}')
    True
    >>> is_manual_format_string('Auto: only un-indexed and un-named: {} {}...')
    False
    >>> is_manual_format_string('Hybrid: at least a {}, and a {0} or a {name}')
    False
    >>> is_manual_format_string('No formatting is both manual and automatic formatting!')
    True
    """
    return is_manual_format_params(format_params_in_str_format(format_string))


def is_automatic_format_string(format_string):
    """ Says if the format_string is uses automatic specification
    See Also: is_manual_format_params
    >>> is_automatic_format_string('Manual: indices: {1} {2}, named: {named} {fields}')
    False
    >>> is_automatic_format_string('Auto: only un-indexed and un-named: {} {}...')
    True
    >>> is_automatic_format_string('Hybrid: at least a {}, and a {0} or a {name}')
    False
    >>> is_manual_format_string('No formatting is both manual and automatic formatting!')
    True
    """
    return is_automatic_format_params(format_params_in_str_format(format_string))


def is_hybrid_format_string(format_string):
    """ Says if the format_params is from a hybrid of auto and manual.
    Note: Hybrid specifications are considered non-valid and can't be formatted with format_string.format(...).
    Yet, it can be useful for flexibility of expression (but will need to be resolved to be used).

    >>> is_hybrid_format_string('Manual: indices: {1} {2}, named: {named} {fields}')
    False
    >>> is_hybrid_format_string('Auto: only un-indexed and un-named: {} {}...')
    False
    >>> is_hybrid_format_string('Hybrid: at least a {}, and a {0} or a {name}')
    True
    >>> is_manual_format_string('No formatting is both manual and automatic formatting (so hybrid is both)!')
    True
    """
    return is_hybrid_format_params(format_params_in_str_format(format_string))


def is_manual_format_params(format_params):
    """ Says if the format_params is from a manual specification
    See Also: is_automatic_format_params
    """
    assert not isinstance(format_params, str), \
        "format_params can't be a string (perhaps you meant is_manual_format_string?)"
    return all((x is not None) for x in format_params)


def is_automatic_format_params(format_params):
    """ Says if the format_params is from an automatic specification
    See Also: is_manual_format_params and is_hybrid_format_params
    """
    assert not isinstance(format_params, str), \
        "format_params can't be a string (perhaps you meant is_automatic_format_string?)"
    return all((x is None) for x in format_params)


def is_hybrid_format_params(format_params):
    """ Says if the format_params is from a hybrid of auto and manual.
    Note: Hybrid specifications are considered non-valid and can't be formatted with format_string.format(...).
    Yet, it can be useful for flexibility of expression (but will need to be resolved to be used).
    See Also: is_manual_format_params and is_automatic_format_params
    """
    assert not isinstance(format_params, str), \
        "format_params can't be a string (perhaps you meant is_hybrid_format_string?)"
    return (not is_manual_format_params(format_params)) and (not is_automatic_format_params(format_params))


def empty_arg_and_kwargs_for_format(format_string, fill_val=None):
    format_params = format_params_in_str_format(format_string)
    if is_manual_format_params(format_params):
        args_keys, kwargs_keys = args_and_kwargs_indices(format_string)
        args = [fill_val] * (max(args_keys) + 1)  # max because e.g., sometimes, we have {0} and {2} without a {1}
        kwargs = {k: fill_val for k in kwargs_keys}
    elif is_automatic_format_params(format_params):
        args = [fill_val] * len(format_params)
        kwargs = {}
    else:
        raise no_hybrid_format_error
        # filled_format_string = mk_manual_spec_format_string(format_string, names=())

    return args, kwargs


# def mk_manual_spec_format_string(format_string, names=()):
#     pass


def args_and_kwargs_indices(format_string):
    """ Get the sets of indices and names used in manual specification of format strings, or None, None if auto spec.
    Args:
        format_string: A format string (i.e. a string with {...} to mark parameter placement and formatting

    Returns:
        None, None if format_string is an automatic specification
        set_of_indices_used, set_of_fields_used if it is a manual specification
    >>> format_string = '{0} (no 1) {2}, {see} this, {0} is a duplicate (appeared before) and {name} is string-named'
    >>> assert args_and_kwargs_indices(format_string) == ({0, 2}, {'name', 'see'})
    >>> format_string = 'This is a format string with only automatic field specification: {}, {}, {} etc.'
    >>> args_and_kwargs_indices(format_string)
    (None, None)
    """
    if is_hybrid_format_params(format_string):
        raise no_hybrid_format_error
    d = {True: set(), False: set()}
    for x in format_params_in_str_format(format_string):
        d[isinstance(x, int)].add(x)
    args_keys, kwargs_keys = d[True], d[False]
    if args_keys is not None:
        return args_keys, kwargs_keys
    else:
        return None, None
