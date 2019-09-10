import string

dflt_formatter = string.Formatter()

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


def is_manual_format_params(format_params):
    """ Says if the format_params is from a manual specification
    >>> is_manual_format_params(format_params_in_str_format('Manual: indices: {1} {2}, named: {named} {fields}'))
    True
    >>> is_manual_format_params(format_params_in_str_format('Auto: only un-indexed and un-named: {} {}...'))
    False
    >>> is_manual_format_params(format_params_in_str_format('Hybrid: at least a {}, and a {0} or a {name}'))
    False
    """
    return all((x is not None) for x in format_params)


def is_automatic_format_params(format_params):
    """ Says if the format_params is from an automatic specification
    >>> is_automatic_format_params(format_params_in_str_format('Manual: indices: {1} {2}, named: {named} {fields}'))
    False
    >>> is_automatic_format_params(format_params_in_str_format('Auto: only un-indexed and un-named: {} {}...'))
    True
    >>> is_automatic_format_params(format_params_in_str_format('Hybrid: at least a {}, and a {0} or a {name}'))
    False
    """
    return all((x is None) for x in format_params)


def is_hybrid_format_params(format_params):
    """ Says if the format_params is from a hybrid of auto and manual.
    Note: Hybrid specifications are considered non-valid and can't be formatted with format_string.format(...).
    Yet, it can be useful for flexibility of expression (but will need to be resolved to be used).

    >>> is_hybrid_format_params(format_params_in_str_format('Manual: indices: {1} {2}, named: {named} {fields}'))
    False
    >>> is_hybrid_format_params(format_params_in_str_format('Auto: only un-indexed and un-named: {} {}...'))
    False
    >>> is_hybrid_format_params(format_params_in_str_format('Hybrid: at least a {}, and a {0} or a {name}'))
    True
    """
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
