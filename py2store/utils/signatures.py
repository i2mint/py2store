from functools import reduce
from inspect import Signature, Parameter, _empty, _ParameterKind, signature
from typing import Any

mappingproxy = type(Signature().parameters)


# PATTERN: tree crud pattern
def signature_to_dict(sig: Signature):
    return {'parameters': sig.parameters, 'return_annotation': sig.return_annotation}


# TODO: will we need more options for the priority argument? Like position?
def update_signature_with_signatures_from_funcs(*funcs, priority: str = 'last'):
    """Make a decorator that will merge the signatures of given funcs to the signature of the wrapped func.
    By default, the funcs signatures will be placed last, but can be given priority by asking priority = 'first'

    >>> def foo(a='a', b: int=0, c=None) -> int: ...
    >>> def bar(b: float=0.0, d: str='hi') -> float: ...
    >>> def something(y=(1, 2)): ...
    >>> def another(y=10): ...
    >>> @update_signature_with_signatures_from_funcs(foo, bar)
    ... def hello(x: str='hi', y=1) -> str:
    ...     pass
    >>> signature(hello)
    <Signature (x: str = 'hi', y=1, a='a', b: float = 0.0, c=None, d: str = 'hi')>
    >>>
    >>> # Try a different order and priority == 'first'. Notice the b arg type and default!
    >>> add_foobar_to_signature_first = update_signature_with_signatures_from_funcs(bar, foo, priority='first')
    >>> bar_foo_something = add_foobar_to_signature_first(something)
    >>> signature(bar_foo_something)
    <Signature (b: int = 0, d: str = 'hi', a='a', c=None, y=(1, 2))>
    >>> # See how you can reuse the decorator several times
    >>> bar_foo_another = add_foobar_to_signature_first(another)
    >>> signature(bar_foo_another)
    <Signature (b: int = 0, d: str = 'hi', a='a', c=None, y=10)>
    """
    if not isinstance(priority, str):
        raise TypeError("priority should be a string")

    if priority == 'last':
        def transform_signature(func):
            func.__signature__ = _merged_signatures_of_func_list([func] + list(funcs))
            return func
    elif priority == 'first':
        def transform_signature(func):
            func.__signature__ = _merged_signatures_of_func_list(list(funcs) + [func])
            return func
    else:
        raise ValueError("priority should be 'last' or 'first'")

    return transform_signature


def common_and_diff_argnames(func1: callable, func2: callable) -> dict:
    """Get list of argument names that are common to two functions, as well as the two lists of names that are different

    Args:
        func1: First function
        func2: Second function

    Returns: A dict with fields 'common', 'func1_not_func2', and 'func2_not_func1'

    >>> def f(t, h, i, n, k): ...
    >>> def g(t, w, i, c, e): ...
    >>> common_and_diff_argnames(f, g)
    {'common': ['t', 'i'], 'func1_not_func2': ['h', 'n', 'k'], 'func2_not_func1': ['w', 'c', 'e']}
    >>> common_and_diff_argnames(g, f)
    {'common': ['t', 'i'], 'func1_not_func2': ['w', 'c', 'e'], 'func2_not_func1': ['h', 'n', 'k']}
    """
    p1 = signature(func1).parameters
    p2 = signature(func2).parameters
    return {
        'common': [x for x in p1 if x in p2],
        'func1_not_func2': [x for x in p1 if x not in p2],
        'func2_not_func1': [x for x in p2 if x not in p1],
    }


dflt_name_for_kind = {
    Parameter.VAR_POSITIONAL: 'args',
    Parameter.VAR_KEYWORD: 'kwargs',
}

arg_order_for_param_tuple = ('name', 'default', 'annotation', 'kind')


def mk_param(param, dflt_kind=Parameter.POSITIONAL_OR_KEYWORD):
    """Make an inspect.Parameter object with less boilerplate verbosity.
    Args:
        param: Can be an inspect.Parameter itself, or something resolving to it:
            - a string: Will be considered to be the argument name
            - an inspect._ParameterKind type: Can only be Parameter.VAR_KEYWORD or Parameter.VAR_POSITIONAL,
                will be taken as the kind, and the name will be decided according to the dflt_name_for_kind mapping.
            - a tuple: Will use the arg_order_for_param_tuple to resolve what Parameter constructor arguments
                the elements of the tuple correspond to.
        dflt_kind: Default kind (of type _ParameterKind) to use if no other kind is specified.

    Returns:
        An inspect.Parameter object

    See mk_signature for uses
    """
    if isinstance(param, str):  # then consider param to be the argument name
        param = dict(name=param)
    elif isinstance(param, _ParameterKind):  # then consider param to be the argument kind
        name = dflt_name_for_kind.get(param, None)
        if name is not None:
            param = dict(name=name, kind=param)
        else:
            raise ValueError("If param is an inspect._ParameterKind, is must be VAR_POSITIONAL or VAR_KEYWORD")
    elif isinstance(param, tuple):
        param = dict(zip(arg_order_for_param_tuple, param))

    if isinstance(param, dict):
        param = dict({'kind': dflt_kind}, **param)
        param = Parameter(**param)

    assert isinstance(param, Parameter), "param should be an inspect.Parameter at this point!"
    return param


def mk_signature(parameters, *, return_annotation=_empty, __validate_parameters__=True):
    """Make an inspect.Signature object with less boilerplate verbosity.
    Args:
        signature: A list of parameter specifications. This could be an inspect.Parameter object or anything that
            the mk_param function can resolve into an inspect.Parameter object.
        return_annotation: Passed on to inspect.Signature.
        __validate_parameters__: Passed on to inspect.Signature.

    Returns:
        An inspect.Signature object

    >>> mk_signature(['a', 'b', 'c'])
    <Signature (a, b, c)>
    >>> mk_signature(['a', ('b', None), ('c', 42, int)])  # specifying defaults and annotations
    <Signature (a, b=None, c: int = 42)>
    >>> import inspect
    >>> mk_signature(['a', ('b', inspect._empty, int)])  # specifying an annotation without a default
    <Signature (a, b: int)>
    >>> mk_signature(['a', 'b', 'c'], return_annotation=str)  # specifying return annotation
    <Signature (a, b, c) -> str>
    >>>
    >>> # But you can always specify parameters the "long" way
    >>> mk_signature([inspect.Parameter(name='kws', kind=inspect.Parameter.VAR_KEYWORD)], return_annotation=str)
    <Signature (**kws) -> str>
    >>>
    >>> # Note that mk_signature is an inverse of signature_to_dict:
    >>> def foo(a, b: int=0, c=None) -> int: ...
    >>> sig_foo = signature(foo)
    >>> assert mk_signature(**signature_to_dict(sig_foo)) == sig_foo
    """
    if isinstance(parameters, Signature):
        parameters = parameters.parameters.values()
    elif isinstance(parameters, (mappingproxy, dict)):
        parameters = parameters.values()
    else:
        parameters = list(map(mk_param, parameters))

    return Signature(parameters,
                     return_annotation=return_annotation, __validate_parameters__=__validate_parameters__)


def set_signature_of_func(func, parameters, *, return_annotation=_empty, __validate_parameters__=True):
    """Set the signature of a function, with sugar.

    Args:
        func: Function whose signature you want to set
        signature: A list of parameter specifications. This could be an inspect.Parameter object or anything that
            the mk_param function can resolve into an inspect.Parameter object.
        return_annotation: Passed on to inspect.Signature.
        __validate_parameters__: Passed on to inspect.Signature.

    Returns:
        None (but sets the signature of the input function)

    >>> import inspect
    >>> def foo(*args, **kwargs):
    ...     pass
    ...
    >>> inspect.signature(foo)
    <Signature (*args, **kwargs)>
    >>> set_signature_of_func(foo, ['a', 'b', 'c'])
    >>> inspect.signature(foo)
    <Signature (a, b, c)>
    >>> set_signature_of_func(foo, ['a', ('b', None), ('c', 42, int)])  # specifying defaults and annotations
    >>> inspect.signature(foo)
    <Signature (a, b=None, c: int = 42)>
    >>> set_signature_of_func(foo, ['a', 'b', 'c'], return_annotation=str)  # specifying return annotation
    >>> inspect.signature(foo)
    <Signature (a, b, c) -> str>
    >>> # But you can always specify parameters the "long" way
    >>> set_signature_of_func(
    ...  foo,
    ...  [inspect.Parameter(name='kws', kind=inspect.Parameter.VAR_KEYWORD)], return_annotation=str)
    >>> inspect.signature(foo)
    <Signature (**kws) -> str>

    """
    func.__signature__ = mk_signature(parameters,
                                      return_annotation=return_annotation,
                                      __validate_parameters__=__validate_parameters__)
    # Not returning func so it's clear(er) that the function is transformed in place


# TODO: It seems the better choice would be to oblige the user to deal with return annotation explicitly

def _merge_sig_dicts(sig1_dict, sig2_dict):
    """Merge two signature dicts. A in dict.update(sig1_dict, **sig2_dict), but specialized for signature dicts.
    If sig1_dict and sig2_dict both define a parameter or return annotation, sig2_dict decides on what the output is.
    """
    return {
        'parameters':
            dict(sig1_dict['parameters'], **sig2_dict['parameters']),
        'return_annotation':
            sig2_dict['return_annotation'] or sig1_dict['return_annotation']
    }


def _merge_signatures(sig1, sig2):
    """Get the merged signatures of two signatures (sig2 is the final decider of conflics)
    >>> def foo(a='a', b: int=0, c=None) -> int: ...
    >>> def bar(b: float=0.0, d: str='hi') -> float: ...
    >>> foo_sig = signature(foo)
    >>> bar_sig = signature(bar)
    >>> foo_sig
    <Signature (a='a', b: int = 0, c=None) -> int>
    >>> bar_sig
    <Signature (b: float = 0.0, d: str = 'hi') -> float>
    >>> _merge_signatures(foo_sig, bar_sig)
    <Signature (a='a', b: float = 0.0, c=None, d: str = 'hi') -> float>
    >>> _merge_signatures(bar_sig, foo_sig)
    <Signature (b: int = 0, d: str = 'hi', a='a', c=None) -> int>
    """
    return mk_signature(**_merge_sig_dicts(signature_to_dict(sig1), signature_to_dict(sig2)))


def _merge_signatures_of_funcs(func1, func2):
    """Get the merged signatures of two functions (func2 is the final decider of conflics)
    >>> def foo(a='a', b: int=0, c=None) -> int: ...
    >>> def bar(b: float=0.0, d: str='hi') -> float: ...
    >>> _merge_signatures_of_funcs(foo, bar)
    <Signature (a='a', b: float = 0.0, c=None, d: str = 'hi') -> float>
    >>> _merge_signatures_of_funcs(bar, foo)
    <Signature (b: int = 0, d: str = 'hi', a='a', c=None) -> int>
    """
    return _merge_signatures(signature(func1), signature(func2))


def _merged_signatures_of_func_list(funcs, return_annotation: Any = _empty):
    """
    >>> def foo(a='a', b: int=0, c=None) -> int: ...
    >>> def bar(b: float=0.0, d: str='hi') -> float: ...
    >>> def hello(x: str='hi', y=1) -> str: ...
    >>>
    >>> # Test how the order of the functions affect the order of the parameters
    >>> _merged_signatures_of_func_list([foo, bar, hello])
    <Signature (a='a', b: float = 0.0, c=None, d: str = 'hi', x: str = 'hi', y=1)>
    >>> _merged_signatures_of_func_list([hello, foo, bar])
    <Signature (x: str = 'hi', y=1, a='a', b: float = 0.0, c=None, d: str = 'hi')>
    >>> _merged_signatures_of_func_list([foo, bar, hello])
    <Signature (a='a', b: float = 0.0, c=None, d: str = 'hi', x: str = 'hi', y=1)>
    >>>
    >>> # Test the return_annotation argument
    >>> _merged_signatures_of_func_list([foo, bar], list)  # specifying that the return type is a list
    <Signature (a='a', b: float = 0.0, c=None, d: str = 'hi') -> list>
    >>> _merged_signatures_of_func_list([foo, bar], foo)  # specifying that the return type is a list
    <Signature (a='a', b: float = 0.0, c=None, d: str = 'hi') -> int>
    >>> _merged_signatures_of_func_list([foo, bar], bar)  # specifying that the return type is a list
    <Signature (a='a', b: float = 0.0, c=None, d: str = 'hi') -> float>
    """

    s = reduce(_merge_signatures, map(signature, funcs))

    if return_annotation in funcs:  # then you want the return annotation of a specific func of funcs
        return_annotation = signature(return_annotation).return_annotation

    return s.replace(return_annotation=return_annotation)
