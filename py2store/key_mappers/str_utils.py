import string

dflt_formatter = string.Formatter()


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
    >>> list(format_params_in_str_format(format_string))
    [0, 2, 0, None, 'name']
    """
    return map(lambda x: int(x) if str.isnumeric(x) else x if x != '' else None,
               filter(_is_not_none, (x[1] for x in dflt_formatter.parse(format_string))))


def n_format_params_in_str_format(format_string):
    """ The number of parameters"""
    return len(set(format_params_in_str_format(format_string)))


def arg_and_kwargs_indices(format_string):
    """

    Args:
        format_string: A format string (i.e. a string with {...} to mark parameter placement and formatting

    Returns:

    >>> format_string = '{0} (no 1) {2}, {see} this, {0} is a duplicate (appeared before) and {name} is string-named'
    >>> assert arg_and_kwargs_indices(format_string) == ({0, 2}, {'name', 'see'})
    >>> format_string = 'This is a format string with only automatic field specification: {}, {}, {} etc.'
    >>> arg_and_kwargs_indices(format_string)
    (None, None)
    """
    d = {True: set(), False: set()}
    for x in format_params_in_str_format(format_string):
        d[isinstance(x, int)].add(x)
    args_keys, kwargs_keys = _validate_str_format_arg_and_kwargs_keys(d[True], d[False])
    return args_keys, kwargs_keys


def _validate_str_format_arg_and_kwargs_keys(args_keys, kwargs_keys):
    """check that str_format is entirely manual or entirely automatic field specification"""
    if any(not x for x in kwargs_keys):  # {} (automatic field numbering) show up as '' in args_keys
        # so need to check that args_keys is empty and kwargs has only None (no "manual" names)
        if (len(args_keys) != 0) or (len(kwargs_keys) != 1):
            raise ValueError(
                f"cannot switch from manual field specification (i.e. {{number}} or {{name}}) "
                "to automatic (i.e. {}) field numbering. But you did:\n{str_format}")
        return None, None
    else:
        return args_keys, kwargs_keys
