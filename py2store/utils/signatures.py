from functools import reduce
from inspect import Signature, Parameter, signature
from typing import Any, Union, Callable, Iterable
from typing import Mapping as MappingType

_empty = Parameter.empty
empty = _empty

_ParameterKind = type(Parameter(name='param_kind', kind=Parameter.POSITIONAL_OR_KEYWORD))
ParamsType = Iterable[Parameter]
ParamsAble = Union[ParamsType, MappingType[str, Parameter], Callable]
SignatureAble = Union[Signature, Callable, ParamsType, MappingType[str, Parameter]]
HasParams = Union[Iterable[Parameter], MappingType[str, Parameter], Signature, Callable]

# short hands for Parameter kinds
PK = Parameter.POSITIONAL_OR_KEYWORD
VP, VK = Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD
PO, KO = Parameter.POSITIONAL_ONLY, Parameter.KEYWORD_ONLY
var_param_kinds = {VP, VK}
var_param_types = var_param_kinds  # Deprecate: for back-compatibility. Delete in 2021


# TODO: Couldn't make this work. See https://www.python.org/dev/peps/pep-0562/
# deprecated_names = {'assure_callable', 'assure_signature', 'assure_params'}
#
#
# def __getattr__(name):
#     print(name)
#     if name in deprecated_names:
#         from warnings import warn
#         warn(f"{name} is deprecated (see code for new name -- look for aliases)", DeprecationWarning)
#     raise AttributeError(f"module {__name__} has no attribute {name}")


def ensure_callable(obj: SignatureAble):
    if isinstance(obj, Callable):
        return obj
    else:
        def f(*args, **kwargs):
            """Empty function made just to carry a signature"""

        f.__signature__ = ensure_signature(obj)
        return f


assure_callable = ensure_callable  # alias for backcompatibility


def ensure_signature(obj: SignatureAble):
    if isinstance(obj, Signature):
        return obj
    elif isinstance(obj, Callable):
        return Signature.from_callable(obj)
    elif isinstance(obj, Iterable):
        params = ensure_params(obj)
        try:
            return Signature(parameters=params)
        except TypeError:
            raise TypeError(f"Don't know how to make that object into a Signature: {obj}")
    elif obj is None:
        return Signature(parameters=())
    # if you get this far...
    raise TypeError(f"Don't know how to make that object into a Signature: {obj}")


assure_signature = ensure_signature  # alias for backcompatibility


def ensure_param(p):
    if isinstance(p, Parameter):
        return p
    elif isinstance(p, dict):
        return Parameter(**p)
    elif isinstance(p, str):
        return Parameter(name=p, kind=PK)
    elif isinstance(p, Iterable):
        name, *r = p
        dflt_and_annotation = dict(zip(['default', 'annotation'], r))
        return Parameter(name, PK, **dflt_and_annotation)
    else:
        raise TypeError(f"Don't know how to make {p} into a Parameter object")


def ensure_params(obj: ParamsAble = None):
    """Get an interable of Parameter instances from an object.

    :param obj:
    :return:

    From a callable:

    >>> def f(w, /, x: float = 1, y=1, *, z: int = 1): ...
    >>> ensure_params(f)
    [<Parameter "w">, <Parameter "x: float = 1">, <Parameter "y=1">, <Parameter "z: int = 1">]

    From an iterable of strings, dicts, or tuples

    >>> ensure_params(['xyz',
    ...     ('b', Parameter.empty, int), # if you want an annotation without a default use Parameter.empty
    ...     ('c', 2),  # if you just want a default, make it the second element of your tuple
    ...     dict(name='d', kind=Parameter.VAR_KEYWORD)])  # all kinds are by default PK: Use dict to specify otherwise.
    [<Parameter "xyz">, <Parameter "b: int">, <Parameter "c=2">, <Parameter "**d">]


    If no input is given, an empty list is returned.

    >>> ensure_params()  # equivalent to ensure_params(None)
    []

    """
    if obj is None:
        return []
    elif isinstance(obj, Iterable):
        if isinstance(obj, str):
            obj = {'name': obj}
        if isinstance(obj, Mapping):
            obj = obj.values()
        obj = list(obj)
        if len(obj) == 0:
            return obj
        else:
            return [ensure_param(p) for p in obj]
    else:
        if isinstance(obj, Parameter):
            obj = Signature([obj])
        elif isinstance(obj, Callable):
            obj = Signature.from_callable(obj)
        elif obj is None:
            obj = {}
        if isinstance(obj, Signature):
            return list(obj.parameters.values())
    # if function didn't return at this point, it didn't find a match, so raise
    raise TypeError(
        f"Don't know how to make that object into an iterable of inspect.Parameter objects: {obj}")


assure_params = ensure_params  # alias for backcompatibility


class MissingArgValFor(object):
    """A simple class to wrap an argument name, indicating that it was missing somewhere.
    >>> MissingArgValFor('argname')
    MissingArgValFor("argname")
    """

    def __init__(self, argname: str):
        assert isinstance(argname, str)
        self.argname = argname

    def __repr__(self):
        return f'MissingArgValFor("{self.argname}")'


# TODO: Look into the handling of the Parameter.VAR_KEYWORD kind in params
def extract_arguments(params: ParamsAble,
                      *,
                      what_to_do_with_remainding='return',
                      include_all_when_var_keywords_in_params=False,
                      assert_no_missing_position_only_args=False,
                      **kwargs
                      ):
    """Extract arguments needed to satisfy the params of a callable, dealing with the dirty details.

    Returns an (param_args, param_kwargs, remaining_kwargs) tuple where
    - param_args are the values of kwargs that are PO (POSITION_ONLY) as defined by params,
    - param_kwargs are those names that are both in params and not in param_args, and
    - remaining_kwargs are the remaining.

    Intended usage: When you need to call a function `func` that has some position-only arguments,
    but you have a kwargs dict of arguments in your hand. You can't just to `func(**kwargs)`.
    But you can (now) do
    ```
    args, kwargs, remaining = extract_arguments(kwargs, func)  # extract from kwargs what you need for func
    # ... check if remaing is empty (or not, depending on your paranoia), and then call the func:
    func(*args, **kwargs)
    ```
    (And if you doing that a lot: Do put it in a decorator!)

    See Also: extract_arguments.without_remainding

    The most frequent case you'll encounter is when there's no POSITION_ONLY args, your param_args will be empty
    and you param_kwargs will contain all the arguments that match params, in the order of these params.

    >>> from inspect import signature
    >>> def f(a, b, c=None, d=0): ...
    >>> extract_arguments(f, b=2, a=1, c=3, d=4, extra='stuff')
    ((), {'a': 1, 'b': 2, 'c': 3, 'd': 4}, {'extra': 'stuff'})

    But sometimes you do have POSITION_ONLY arguments.
    What extract_arguments will do for you is return the value of these as the first element of
    the triple.
    >>> def f(a, b, c=None, /, d=0): ...
    >>> extract_arguments(f, b=2, a=1, c=3, d=4, extra='stuff')
    ((1, 2, 3), {'d': 4}, {'extra': 'stuff'})

    Note above how we get `(1, 2, 3)`, the order defined by the func's signature,
    instead of `(2, 1, 3)`, the order defined by the kwargs.
    So it's the params (e.g. function signature) that determine the order, not kwargs.
    When using to call a function, this is especially crucial if we use POSITION_ONLY arguments.

    See also that the third output, the remaining_kwargs, as `{'extra': 'stuff'}` since
    it was not in the params of the function.
    Even if you include a VAR_KEYWORD kind of argument in the function, it won't change
    this behavior.

    >>> def f(a, b, c=None, /, d=0, **kws): ...
    >>> extract_arguments(f, b=2, a=1, c=3, d=4, extra='stuff')
    ((1, 2, 3), {'d': 4}, {'extra': 'stuff'})

    This is because we don't want to assume that all the kwargs can actually be
    included in a call to the function behind the params.
    Instead, the user can chose whether to include the remainder by doing a:
    ```
    param_kwargs.update(remaining_kwargs)
    ```
    et voilà.

    That said, we do understand that it may be a common pattern, so we'll do that extra step for you
    if you specify `include_all_when_var_keywords_in_params=True`.

    >>> def f(a, b, c=None, /, d=0, **kws): ...
    >>> extract_arguments(f, b=2, a=1, c=3, d=4, extra='stuff',
    ...                     include_all_when_var_keywords_in_params=True)
    ((1, 2, 3), {'d': 4, 'extra': 'stuff'}, {})

    If you're expecting no remainder you might want to just get the args and kwargs (not this third
    expected-to-be-empty remainder). You have two ways to do that, specifying:
        `what_to_do_with_remainding='ignore'`, which will just return the (args, kwargs) pair
        `what_to_do_with_remainding='assert_empty'`, which will do the same, but first assert the remainder is empty
    We suggest to use `functools.partial` to configure the `argument_argument` you need.

    >>> from functools import partial
    >>> arg_extractor = partial(extract_arguments,
    ...     what_to_do_with_remainding='assert_empty',
    ...     include_all_when_var_keywords_in_params=True)
    >>> def f(a, b, c=None, /, d=0, **kws): ...
    >>> arg_extractor(f, b=2, a=1, c=3, d=4, extra='stuff')
    ((1, 2, 3), {'d': 4, 'extra': 'stuff'})

    And what happens if the kwargs doesn't contain all the POSITION_ONLY arguments?

    >>> def f(a, b, c=None, /, d=0): ...
    >>> extract_arguments(f, b=2, d='is a kw arg', e='is not an arg at all')
    ((MissingArgValFor("a"), 2, MissingArgValFor("c")), {'d': 'is a kw arg'}, {'e': 'is not an arg at all'})

    A few more examples...

    Let's call `extract_arguments` with params being not a function,
    but, a Signature instance, a mapping whose values are Parameter instances,
    or an iterable of Parameter instances...

    >>> def func(a, b,  /, c=None, *, d=0, **kws): ...
    >>> sig = Signature.from_callable(func)
    >>> param_map = sig.parameters
    >>> param_iterable = param_map.values()
    >>> kwargs = dict(b=2, a=1, c=3, d=4, extra='stuff')
    >>> assert extract_arguments(sig, **kwargs) == extract_arguments(func, **kwargs)
    >>> assert extract_arguments(param_map, **kwargs) == extract_arguments(func, **kwargs)
    >>> assert extract_arguments(param_iterable, **kwargs) == extract_arguments(func, **kwargs)

    Edge case:
    No params specified? No problem. You'll just get empty args and kwargs. Everything in the remainder
    >>> extract_arguments(params=(), b=2, a=1, c=3, d=0)
    ((), {}, {'b': 2, 'a': 1, 'c': 3, 'd': 0})

    :param params: Specifies what PO arguments should be extracted.
        Could be a callable, Signature, iterable of Parameters...
    :param what_to_do_with_remainding:
        'return' (default): function will return `param_args`, `param_kwargs`, `remaining_kwargs`
        'ignore': function will return `param_args`, `param_kwargs`
        'assert_empty': function will assert that `remaining_kwargs` is empty and then return `param_args`, `param_kwargs`
    :param include_all_when_var_keywords_in_params=False,
    :param assert_no_missing_position_only_args=False,
    :param kwargs: The kwargs to extract the args from
    :return: A (param_args, param_kwargs, remaining_kwargs) tuple.
    """

    assert what_to_do_with_remainding in {'return', 'ignore', 'assert_empty'}
    assert isinstance(include_all_when_var_keywords_in_params, bool)
    assert isinstance(assert_no_missing_position_only_args, bool)

    params = ensure_params(params)
    if not params:
        return (), {}, {k: v for k, v in kwargs.items()}

    params_names = tuple(p.name for p in params)
    names_for_args = [p.name for p in params if p.kind == Parameter.POSITIONAL_ONLY]
    param_kwargs_names = [x for x in params_names if x not in set(names_for_args)]
    remaining_names = [x for x in kwargs if x not in params_names]

    param_args = tuple(kwargs.get(k, MissingArgValFor(k)) for k in names_for_args)
    param_kwargs = {k: kwargs[k] for k in param_kwargs_names if k in kwargs}
    remaining_kwargs = {k: kwargs[k] for k in remaining_names}

    if include_all_when_var_keywords_in_params:
        if next((p.name for p in params if p.kind == Parameter.VAR_KEYWORD), None) is not None:
            param_kwargs.update(remaining_kwargs)
            remaining_kwargs = {}

    if assert_no_missing_position_only_args:
        missing_argnames = tuple(x.argname for x in param_args if isinstance(x, MissingArgValFor))
        assert not missing_argnames, f"There were some missing positional only argnames: {missing_argnames}"

    if what_to_do_with_remainding == 'return':
        return param_args, param_kwargs, remaining_kwargs
    elif what_to_do_with_remainding == 'ignore':
        return param_args, param_kwargs
    elif what_to_do_with_remainding == 'assert_empty':
        assert len(remaining_kwargs) == 0, f"remaining_kwargs not empty: remaining_kwargs={remaining_kwargs}"
        return param_args, param_kwargs


from functools import partial

extract_arguments_ignoring_remainder = partial(extract_arguments,
                                               what_to_do_with_remainding='ignore')
extract_arguments_asserting_no_remainder = partial(extract_arguments,
                                                   what_to_do_with_remainding='assert_empty')

from collections.abc import Mapping
from typing import Optional, Iterable
from dataclasses import dataclass


@dataclass
class Command:
    """A dataclass that holds a `(caller, args, kwargs)` triple and allows one to execute `caller(*args, **kwargs)`

    :param caller: A callable that will be called with (*args, **kwargs) argument
    :param args: A tuple
    :param kwargs:
    """
    caller: callable
    args: Iterable = ()
    kwargs: Optional[dict] = None

    def __post_init__(self):
        assert isinstance(self.args, Iterable)
        self.kwargs = self.kwargs or {}
        assert isinstance(self.kwargs, Mapping)

    def __call__(self):
        return self.caller(*self.args, **self.kwargs)


def extract_commands(funcs, *,
                     mk_command: Callable[[Callable, tuple, dict], Any] = Command,
                     what_to_do_with_remainding='ignore',
                     **kwargs):
    """

    :param funcs:
    :param mk_command:
    :param kwargs:
    :return:

    >>> def add(a, b: float = 0.0) -> float:
    ...     return a + b
    >>> def mult(x: float, y=1):
    ...     return x * y
    >>> def formula1(w, /, x: float, y=1, *, z: int = 1):
    ...     return ((w + x) * y) ** z
    >>> commands = extract_commands((add, mult, formula1), a=1, b=2, c=3, d=4, e=5, w=6, x=7)
    >>> for command in commands:
    ...     print(f"Calling {command.caller.__name__} with args={command.args} and kwargs={command.kwargs}")
    ...     print(command())
    ...
    Calling add with args=() and kwargs={'a': 1, 'b': 2}
    3
    Calling mult with args=() and kwargs={'x': 7}
    7
    Calling formula1 with args=(6,) and kwargs={'x': 7}
    13
    """
    extract = partial(extract_arguments,
                      what_to_do_with_remainding=what_to_do_with_remainding,
                      include_all_when_var_keywords_in_params=False,
                      assert_no_missing_position_only_args=True)

    if callable(funcs):
        funcs = [funcs]

    for func in funcs:
        func_args, func_kwargs = extract(func, **kwargs)
        yield mk_command(func, func_args, func_kwargs)


def commands_dict(funcs, *,
                  mk_command: Callable[[Callable, tuple, dict], Any] = Command,
                  what_to_do_with_remainding='ignore',
                  **kwargs):
    """

    :param funcs:
    :param mk_command:
    :param kwargs:
    :return:

    >>> def add(a, b: float = 0.0) -> float:
    ...     return a + b
    >>> def mult(x: float, y=1):
    ...     return x * y
    >>> def formula1(w, /, x: float, y=1, *, z: int = 1):
    ...     return ((w + x) * y) ** z
    >>> d = commands_dict((add, mult, formula1), a=1, b=2, c=3, d=4, e=5, w=6, x=7)
    >>> d[add]()
    3
    >>> d[mult]()
    7
    >>> d[formula1]()
    13

    """
    if callable(funcs):
        funcs = [funcs]
    it = extract_commands(funcs, what_to_do_with_remainding=what_to_do_with_remainding,
                          mk_command=mk_command, **kwargs)
    return dict(zip(funcs, it))


class Param(Parameter):
    # aliases
    PK = Parameter.POSITIONAL_OR_KEYWORD
    OP = Parameter.POSITIONAL_ONLY
    OK = Parameter.KEYWORD_ONLY
    VP = Parameter.VAR_POSITIONAL
    VK = Parameter.VAR_KEYWORD

    def __init__(self, name, kind=PK, *, default=empty, annotation=empty):
        super().__init__(name, kind, default=default, annotation=annotation)


def param_has_default_or_is_var_kind(p: Parameter):
    return p.default != Parameter.empty or p.kind in var_param_kinds


WRAPPER_UPDATES = ('__dict__',)

from functools import wraps


# TODO: See other signature operating functions below in this module:
#   Do we need them now that we have Sig?
#   Do we want to keep them and have Sig use them?
class Sig(Signature, Mapping):
    """A subclass of inspect.Signature that has some extra api sugar, such as a dict-like interface, merging, ...

    You can construct a `Sig` object from a callable,

    >>> def f(w, /, x: float = 1, y=1, *, z: int = 1): ...
    >>> Sig(f)
    <Sig (w, /, x: float = 1, y=1, *, z: int = 1)>

    but also from any "ParamsAble" object. Such as...
    an iterable of Parameter instances, strings, tuples, or dicts:

    >>> Sig(['a', ('b', Parameter.empty, int), ('c', 2), ('d', 1.0, float),
    ...                dict(name='special', kind=Parameter.KEYWORD_ONLY, default=0)])
    <Sig (a, b: int, c=2, d: float = 1.0, *, special=0)>
    >>>
    >>> Sig(['a', 'b', dict(name='args', kind=Parameter.VAR_POSITIONAL),
    ...                dict(name='kwargs', kind=Parameter.VAR_KEYWORD)]
    ... )
    <Sig (a, b, *args, **kwargs)>

    The parameters of a signature are like a matrix whose rows are the parameters,
    and the 4 columns are their properties: name, kind, default, and annotation
    (the two laste ones being optional).
    You get a row view when doing `Sig(...).parameters.values()`,
    but what if you want a column-view?
    Here's how:

    >>> def f(w, /, x: float = 1, y=2, *, z: int = 3): ...
    >>>
    >>> s = Sig(f)
    >>> s.kinds  # doctest: +NORMALIZE_WHITESPACE
    {'w': <_ParameterKind.POSITIONAL_ONLY: 0>,
    'x': <_ParameterKind.POSITIONAL_OR_KEYWORD: 1>,
    'y': <_ParameterKind.POSITIONAL_OR_KEYWORD: 1>,
    'z': <_ParameterKind.KEYWORD_ONLY: 3>}

    >>> s.annotations
    {'x': <class 'float'>, 'z': <class 'int'>}
    >>> assert s.annotations == f.__annotations__  # same as what you get in `__annotations__`
    >>>
    >>> s.defaults
    {'x': 1, 'y': 2, 'z': 3}
    >>> # Note that it's not the same as you get in __defaults__ though:
    >>> assert s.defaults != f.__defaults__ == (1, 2)  # not 3, since __kwdefaults__ has that!

    We can sum (i.e. merge) and subtract (i.e. remove arguments) Sig instances.
    Also, Sig instance is callable. It has the effect of inserting it's signature in the input
    (in `__signature__`, but also inserting the resulting `__defaults__` and `__kwdefaults__`).
    One of the intents is to be able to do things like:

    >>> import inspect
    >>> def f(w, /, x: float = 1, y=1, *, z: int = 1): ...
    >>> def g(i, w, j=2): ...
    >>>
    >>> @Sig.from_objs(f, g, ['a', ('b', 3.14), ('c', 42, int)])
    ... def some_func(*args, **kwargs):
    ...     ...
    >>> inspect.signature(some_func)
    <Signature (w, i, a, x: float = 1, y=1, z: int = 1, j=2, b=3.14, c: int = 42)>
    >>>
    >>> sig = Sig(f) + g + ['a', ('b', 3.14), ('c', 42, int)] - 'b' - ['a', 'z']
    >>> @sig
    ... def some_func(*args, **kwargs):
    ...     ...
    >>> inspect.signature(some_func)
    <Signature (w, i, x: float = 1, y=1, j=2, c: int = 42)>

    """

    def __init__(self, obj: ParamsAble = None, *,
                 return_annotation=empty,
                 __validate_parameters__=True, ):
        """Initialize a Sig instance.
        See Also: `ensure_params` to see what kind of objects you can make `Sig`s with.

        :param obj: A ParamsAble object, which could be:
            - a callable,
            - and iterable of Parameter instances
            - an iterable of strings (representing annotation-less, default-less) argument names,
            - tuples: (argname, default) or (argname, default, annotation),
            - dicts: ``{'name': REQUIRED,...}`` with optional `kind`, `default` and `annotation` fields
            - None (which will produce an argument-less Signature)

        >>> Sig(['a', 'b', 'c'])
        <Sig (a, b, c)>
        >>> Sig(['a', ('b', None), ('c', 42, int)])  # specifying defaults and annotations
        <Sig (a, b=None, c: int = 42)>
        >>> import inspect
        >>> Sig(['a', ('b', inspect._empty, int)])  # specifying an annotation without a default
        <Sig (a, b: int)>
        >>> Sig(['a', 'b', 'c'], return_annotation=str)  # specifying return annotation
        <Sig (a, b, c) -> str>

        But you can always specify parameters the "long" way

        >>> Sig([inspect.Parameter(name='kws', kind=inspect.Parameter.VAR_KEYWORD)], return_annotation=str)
        <Sig (**kws) -> str>

        And note that:
        >>> Sig()
        <Sig ()>
        >>> Sig(None)
        <Sig ()>
        """
        if callable(obj) and return_annotation is empty:
            return_annotation = Signature.from_callable(obj).return_annotation
        super().__init__(ensure_params(obj),
                         return_annotation=return_annotation,
                         __validate_parameters__=__validate_parameters__)

    def wrap(self, func: Callable):
        """Gives the input function the signature.
        This is similar to the `functools.wraps` function, but parametrized by a signature
        (not a callable). Also, where as both write to the input func's `__signature__`
        attribute, here we also write to
        - `__defaults__` and `__kwdefaults__`, extracting these from `__signature__`
            (functools.wraps doesn't do that at the time of writing this
            (see https://github.com/python/cpython/pull/21379)).
        - `__annotations__` (also extracted from `__signature__`)
        - does not write to `__module__`, `__name__`, `__qualname__`, `__doc__`
            (because again, we're basinig the injecton on a signature, not a function,
            so we have no name, doc, etc...)

        >>> def f(w, /, x: float = 1, y=2, z: int = 3):
        ...     return w + x * y ** z
        >>> f(0, 1)  # 0 + 1 * 2 ** 3
        8
        >>> f.__defaults__
        (1, 2, 3)
        >>> assert 8 == f(0) == f(0, 1) == f(0, 1, 2) == f(0, 1, 2, 3)

        Now let's create a very similar function to f, but where:
        - w is not position-only
        - x annot is int instead of float, and doesn't have a default
        - z's default changes to 10
        >>> def g(w, x: int, y=2, z: int = 10):
        ...     return w + x * y ** z
        >>> s = Sig(g)
        >>> f = s.wrap(f)
        >>> import inspect
        >>> inspect.signature(f)  # see that
        <Signature (w, x: int, y=2, z: int = 10)>
        >>> # But (unlike with functools.wraps) here we get __defaults__ and __kwdefault__
        >>> f.__defaults__  # see that x has no more default, and z's default changed to 10
        (2, 10)
        >>> f(0, 1)  # see that now we get a different output because using different defaults
        1024

        TODO: Something goes wrong when using keyword only arguments.
            Note that the same problem occurs with functools.wraps, and even boltons.funcutils.wraps.
        >>> def f(w, /, x: float = 1, y=2, *, z: int = 3):
        ...     return w + x * y ** z
        >>> f(0)  # 0 + 1 * 2 ** 3
        8
        >>> f(0, 1, 2, 3)  # error expected!
        Traceback (most recent call last):
          ...
        TypeError: f() takes from 1 to 3 positional arguments but 4 were given
        >>> def g(w, x: int, y=2, *, z: int = 10):
        ...     return w + x * y ** z
        >>> s = Sig(g)
        >>> f = s.wrap(f)
        >>> f.__defaults__
        (2,)
        >>> f.__kwdefaults__
        {'z': 10}
        >>> f(0, 1, 2, 3)  # error not expected! TODO: Make it work!!
        Traceback (most recent call last):
          ...
        TypeError: f() takes from 2 to 3 positional arguments but 4 were given
        """
        func.__signature__ = Signature(self.parameters.values(),
                                       return_annotation=self.return_annotation)
        func.__annotations__ = self.annotations
        # endow the function with __defaults__ and __kwdefaults__ (not the default of functools.wraps!)
        func.__defaults__, func.__kwdefaults__ = self._dunder_defaults_and_kwdefaults()
        # "copy" over all other non-dunder attributes (not the default of functools.wraps!)
        for attr in filter(lambda x: not x.startswith('__'), dir(func)):
            setattr(func, attr, getattr(func, attr))
        return func

    def __call__(self, func: Callable):
        """Gives the input function the signature.
        Just calls Sig.wrap so see docs of Sig.wrap (which contains examples and doctests).
        """
        return self.wrap(func)

    @classmethod
    def sig_or_none(cls, obj):
        """Returns a Sig instance, or None if there was a ValueError trying to construct it.
        One use case is to be able to tell if an object has a signature or not.

        >>> has_signature = lambda obj: bool(Sig.sig_or_none(obj))
        >>> has_signature(print)
        False
        >>> has_signature(Sig)
        True

        This means we can more easily get signatures in bulk without having to write try/catches:

        >>> len(list(filter(None, map(Sig.sig_or_none, (Sig, print, map, filter, Sig.wrap)))))
        2
        """
        try:
            return (callable(obj) or None) and cls(obj)
        except ValueError:
            return None

    def __bool__(self):
        return True

    def _dunder_defaults_and_kwdefaults(self):
        """Get the __defaults__, __kwdefaults__ (i.e. what would be the dunders baring these names in a python callable)

        >>> def foo(w, /, x: float, y=1, *, z: int = 1): ...
        >>> __defaults__, __kwdefaults__ = Sig(foo)._dunder_defaults_and_kwdefaults()
        >>> __defaults__
        (1,)
        >>> __kwdefaults__
        {'z': 1}
        """
        ko_names = self.names_for_kind(kind=KO)
        dflts = self.defaults
        return (
            tuple(dflts[name] for name in dflts if name not in ko_names),
            # as known as __defaults__ in python callables
            {name: dflts[name] for name in dflts if name in ko_names}  # as known as __kwdefaults__ in python callables
        )

    def to_signature_kwargs(self):
        """The dict of keyword arguments to make this signature instance.

        >>> def f(w, /, x: float = 2, y=1, *, z: int = 0) -> float: ...
        >>> Sig(f).to_signature_kwargs()  # doctest: +NORMALIZE_WHITESPACE
        {'parameters':
            [<Parameter "w">,
            <Parameter "x: float = 2">,
            <Parameter "y=1">,
            <Parameter "z: int = 0">],
        'return_annotation': <class 'float'>}

        Note that this does NOT return:
        ```
                {'parameters': self.parameters,
                'return_annotation': self.return_annotation}
        ```
        which would not actually work as keyword arguments of ``Signature``.
        Yeah, I know. Don't ask me, ask the authors of `Signature`!

        Instead, `parammeters` will be ``list(self.parameters.values())``, which does work.

        """
        return {'parameters': list(self.parameters.values()),
                'return_annotation': self.return_annotation}

    def to_simple_signature(self):
        """A builtin ``inspect.Signature`` instance equivalent (i.e. without the extra properties and methods)

        >>> def f(w, /, x: float = 2, y=1, *, z: int = 0): ...
        >>> Sig(f).to_simple_signature()
        <Signature (w, /, x: float = 2, y=1, *, z: int = 0)>

        """
        return Signature(**self.to_signature_kwargs())

    @classmethod
    def from_objs(cls, *objs, **name_and_dflts):
        objs = list(objs)
        for name, default in name_and_dflts.items():
            objs.append([{'name': name, 'kind': PK, 'default': default}])
        if len(objs) > 0:
            first_obj, *objs = objs
            sig = cls(ensure_params(first_obj))
            for obj in objs:
                sig = sig + obj
            return sig
        else:  # if no objs are given
            return cls()  # return an empty signature

    @classmethod
    def from_params(cls, params):
        if isinstance(params, Parameter):
            params = (params,)
        return cls(params)

    @property
    def params(self):
        """Just list(self.parameters.values()), because that's often what we want.
        Why a Sig.params property when we already have a Sig.parameters property?

        Well, as much as is boggles my mind, it so happens that the Signature.parameters
        is a name->Parameter mapping, but the Signature argument `parameters`, though baring the same name,
        is expected to be a list of Parameter instances.

        So Sig.params is there to restore semantic consistence sanity.
        """
        return list(self.parameters.values())

    @property
    def names(self):
        return list(self.keys())

    @property
    def kinds(self):
        return {p.name: p.kind for p in self.values()}

    @property
    def defaults(self):
        return {p.name: p.default for p in self.values() if p.default != Parameter.empty}

    @property
    def annotations(self):
        """{arg_name: annotation, ...} dict of annotations of the signature.
        What `func.__annotations__` would give you.
        """
        return {p.name: p.annotation for p in self.values() if p.annotation != Parameter.empty}

    # def substitute(self, **sub_for_name):
    #     def gen():
    #
    #         for name, substitution in sub_for_name.items():
    #

    def names_for_kind(self, kind):
        return tuple(p.name for p in self.values() if p.kind == kind)

    def __iter__(self):
        return iter(self.parameters)

    def __len__(self):
        return len(self.parameters)

    def __getitem__(self, k):
        return self.parameters[k]

    @property
    def has_var_kinds(self):
        return any(p.kind in var_param_kinds for p in set(self.values()))

    @property
    def has_var_positional(self):
        return any(p.kind == VP for p in list(self.values()))

    @property
    def has_var_keyword(self):
        return any(p.kind == VK for p in list(self.values()))

    def merge_with_sig(self, sig: ParamsAble, ch_to_all_pk=False):
        """Return a signature obtained by merging self signature with another signature.
        Insofar as it can, given the kind precedence rules, the arguments of self will appear first.

        :param sig: The signature to merge with.
        :param ch_to_all_pk: Whether to change all kinds of both signatures to PK (POSITIONAL_OR_KEYWORD)
        :return:

        >>> from py2store.utils.signatures import Sig, KO
        >>>
        >>> def func(a=None, *, b=1, c=2): ...
        ...
        >>>
        >>> s = Sig(func)
        >>> s
        <Sig (a=None, *, b=1, c=2)>

        Observe where the new arguments ``d`` and ``e`` are placed,
        according to whether they have defaults and what their kind is:

        >>> s.merge_with_sig(['d', 'e'])
        <Sig (d, e, a=None, *, b=1, c=2)>
        >>> s.merge_with_sig(['d', ('e', 4)])
        <Sig (d, a=None, e=4, *, b=1, c=2)>
        >>> s.merge_with_sig(['d', dict(name='e', kind=KO, default=4)])
        <Sig (d, a=None, *, b=1, c=2, e=4)>
        >>> s.merge_with_sig([dict(name='d', kind=KO), dict(name='e', kind=KO, default=4)])
        <Sig (a=None, *, d, b=1, c=2, e=4)>

        If the kind of the params is not important, but order is, you can specify ``ch_to_all_pk=True``:

        >>> s.merge_with_sig(['d', 'e'], ch_to_all_pk=True)
        <Sig (d, e, a=None, b=1, c=2)>
        >>> s.merge_with_sig([('d', 3), ('e', 4)], ch_to_all_pk=True)
        <Sig (a=None, b=1, c=2, d=3, e=4)>

        """
        if ch_to_all_pk:
            _self = Sig(ch_signature_to_all_pk(self))
            _sig = Sig(ch_signature_to_all_pk(ensure_signature(sig)))
        else:
            _self = self
            _sig = Sig(sig)

        _msg = f"\nHappened during an attempt to merge {self} and {sig}"

        assert not _self.has_var_keyword or not _sig.has_var_keyword, \
            f"Can't merge two signatures if they both have a VAR_POSITIONAL parameter:{_msg}"
        assert not _self.has_var_keyword or not _sig.has_var_keyword, \
            "Can't merge two signatures if they both have a VAR_KEYWORD parameter:{_msg}"
        assert all((_self[name].kind, _self[name].default) == (_sig[name].kind, _sig[name].default)
                   for name in _self.keys() & _sig.keys()), \
            f"During a signature merge, if two names are the same, they must have the same kind and default:{_msg}"

        params = list(self._chain_params_of_signatures(
            _self.without_defaults, _sig.without_defaults, _self.with_defaults, _sig.with_defaults))
        params.sort(key=lambda p: p.kind)
        return self.__class__(params)

    def __add__(self, sig: ParamsAble):
        """Merge two signatures (casting all non-VAR kinds to POSITIONAL_OR_KEYWORD before hand)

        Important Notes:
        - The resulting Sig will loose it's return_annotation if it had one.
            This is to avoid making too many assumptions about how the sig sum will be used.
            If a return_annotation is needed (say, for composition, the last return_annotation
            summed), one can subclass Sig and overwrite __add__
        - POSITION_ONLY and KEYWORD_ONLY kinds will be replaced by POSITIONAL_OR_KEYWORD kind.
        This is to simplify the interface and code.
        If the user really wants to maintain those kinds, they can replace them back after the fact.

        >>> def f(w, /, x: float = 1, y=1, *, z: int = 1): ...
        >>> def h(i, j, w): ...  # has a 'w' argument, like f and g
        >>> def different(a, b: str, c=None): ...  # No argument names in common with other functions

        >>> Sig(f) + Sig(different)
        <Sig (w, a, b: str, x: float = 1, y=1, z: int = 1, c=None)>
        >>> Sig(different) + Sig(f)
        <Sig (a, b: str, w, c=None, x: float = 1, y=1, z: int = 1)>

        The order of the first signature will take precedence over the second,
        but default-less arguments have to come before arguments with defaults.
         first, and Note the difference of the orders.
        >>> Sig(f) + Sig(h)
        <Sig (w, i, j, x: float = 1, y=1, z: int = 1)>
        >>> Sig(h) + Sig(f)
        <Sig (i, j, w, x: float = 1, y=1, z: int = 1)>

        The sum of two Sig's takes a safe-or-blow-up-now approach.
        If any of the arguments have different defaults or annotations, summing will raise an AssertionError.
        It's up to the user to decorate their input functions to express the default they actually desire.

        >>> def ff(w, /, x: float, y=1, *, z: int = 1): ...  # just like f, but without the default for x
        >>> Sig(f) + Sig(ff)  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ...
        AssertionError: During a signature merge, if two names are the same, they must have the same kind and default:
        Happened during an attempt to merge (w, /, x: float = 1, y=1, *, z: int = 1) and (w, /, x: float, y=1, *, z: int = 1)


        >>> def hh(i, j, w=1): ...  # like h, but w has a default
        >>> Sig(h) + Sig(hh)  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ...
        AssertionError: During a signature merge, if two names are the same, they must have the same kind and default:
        Happened during an attempt to merge (i, j, w) and (i, j, w=1)


        >>> Sig(f) + ['w', ('y', 1), ('d', 1.0, float),
        ...                dict(name='special', kind=Parameter.KEYWORD_ONLY, default=0)]
        <Sig (w, x: float = 1, y=1, z: int = 1, d: float = 1.0, special=0)>

        """
        return self.merge_with_sig(sig, ch_to_all_pk=True)

    def __radd__(self, sig: ParamsAble):
        """Adding on the right.
        The raison d'être for this is so that you can start your summing with any signature speccifying
         object that Sig will be able to resolve into a signature. Like this:

        >>> ['first_arg', ('second_arg', 42)] + Sig(lambda x, y: x * y)
        <Sig (first_arg, x, y, second_arg=42)>

        Note that the ``second_arg`` doesn't actually end up being the second argument because
        it has a default and x and y don't. But if you did this:

        >>> ['first_arg', ('second_arg', 42)] + Sig(lambda x=0, y=1: x * y)
        <Sig (first_arg, second_arg=42, x=0, y=1)>

        you'd get what you expect.

        Of course, we could have just obliged you to say ``Sig(['first_arg', ('second_arg', 42)])``
        explicitly and spare ourselves yet another method.
        The reason we made ``__radd__`` is so we can make it handle 0 + Sig(...), so that you can
        merge an iterable of signatures like this:

        >>> def f(a, b, c): ...
        >>> def g(c, b, e): ...
        >>> sigs = map(Sig, [f, g])
        >>> sum(sigs)
        <Sig (a, b, c, e)>

        Let's say, for whatever reason (don't ask me), you wanted to make a function that contains all the
        arguments of all the functions of ``os.path`` (that don't contain any var arg kinds).

        >>> import os.path
        >>> funcs = list(filter(callable, (getattr(os.path, a) for a in dir(os.path) if not a.startswith('_'))))
        >>> sigs = filter(lambda sig: not sig.has_var_kinds, map(Sig, funcs))
        >>> sum(sigs)
        <Sig (path, p, paths, m, filename, s, f1, f2, fp1, fp2, s1, s2, start=None)>
        """
        if sig == 0:  # so that we can do ``sum(iterable_of_sigs)``
            sig = Sig([])
        else:
            sig = Sig(sig)
        return sig.merge_with_sig(self)

    def remove_names(self, names):
        names = {p.name for p in ensure_params(names)}
        new_params = {name: p for name, p in self.parameters.items() if name not in names}
        return self.__class__(new_params, return_annotation=self.return_annotation)

    def __sub__(self, sig):
        return self.remove_names(sig)

    @staticmethod
    def _chain_params_of_signatures(*sigs):
        """Yields Parameter instances taken from sigs without repeating the same name twice.
        >>> str(list(Sig._chain_params_of_signatures(Sig(lambda x, *args, y=1: ...),
        ...     Sig(lambda x, y, z, **kwargs: ...))))
        '[<Parameter "x">, <Parameter "*args">, <Parameter "y=1">, <Parameter "z">, <Parameter "**kwargs">]'
        """
        already_merged_names = set()
        for s in sigs:
            for p in s.parameters.values():
                if p.name not in already_merged_names:
                    yield p
                already_merged_names.add(p.name)

    @property
    def without_defaults(self):
        """
        >>> from i2.signatures import Sig
        >>> list(Sig(lambda *args, a, b, x=1, y=1, **kwargs: ...).without_defaults)
        ['a', 'b']
        """
        return self.__class__(p for p in self.values() if not param_has_default_or_is_var_kind(p))

    @property
    def with_defaults(self):
        """
        >>> from i2.signatures import Sig
        >>> list(Sig(lambda *args, a, b, x=1, y=1, **kwargs: ...).with_defaults)
        ['args', 'x', 'y', 'kwargs']
        """
        return self.__class__(p for p in self.values() if param_has_default_or_is_var_kind(p))

    def normalize_kind(self):
        def changed_params():
            for p in self.parameters.values():
                if p.kind not in var_param_kinds:
                    yield p.replace(kind=PK)
                else:
                    yield p

        return self.__class__(list(changed_params()), return_annotation=self.return_annotation)

    def kwargs_from_args_and_kwargs(self, args, kwargs, *,
                                    apply_defaults=False, allow_partial=False, allow_excess=False, ignore_kind=False):
        """Extracts a dict of input argument values for target signature, from args and kwargs.

        When you need to manage how the arguments of a function are specified, you need to take care of
        multiple cases depending on whether they were specified as positional arguments
        (`args`) or keyword arguments (`kwargs`).

        The `kwargs_from_args_and_kwargs` (and it's sorta-inverse inverse, `args_and_kwargs_from_kwargs`)
        are there to help you manage this.

        If you could rely on the the fact that only `kwargs` were given it would reduce the complexity of your code.
        This is why we have the `ch_signature_to_all_pk` function in `signatures.py`.

        We also need to have a means to make a `kwargs` only from the actual `(*args, **kwargs)` used at runtime.
        We have `Signature.bind` (and `bind_partial`) for that.

        But these methods will fail if there is extra stuff in the `kwargs`.
        Yet sometimes we'd like to have a `dict` that services several functions that will extract their needs from it.

        That's where  `Sig.extract_kwargs(*args, **kwargs)` is needed.
        :param args: The args the function will be called with.
        :param kwargs: The kwargs the function will be called with.
        :param apply_defaults: (bool) Whether to apply signature defaults to the non-specified argument names
        :param allow_partial: (bool) True iff you want to allow partial signature fulfillment.
        :param allow_excess: (bool) Set to True iff you want to allow extra kwargs items to be ignored.
        :param ignore_kind: (bool) Set to True iff you want to ignore the position and keyword only kinds,
            in order to be able to accept args and kwargs in such a way that there can be cross-over
            (args that are supposed to be keyword only, and kwargs that are supposed to be positional only)
        :return: An {argname: argval, ...} dict

        See also the sorta-inverse of this function: args_and_kwargs_from_kwargs

        >>> def foo(w, /, x: float, y='YY', *, z: str = 'ZZ'): ...
        >>> sig = Sig(foo)
        >>> assert (
        ...     sig.kwargs_from_args_and_kwargs((11, 22, 'you'), dict(z='zoo'))
        ...     == sig.kwargs_from_args_and_kwargs((11, 22), dict(y='you', z='zoo'))
        ...     == {'w': 11, 'x': 22, 'y': 'you', 'z': 'zoo'})

        By default, `apply_defaults=False`, which will lead to only get those arguments you input.
        >>> sig.kwargs_from_args_and_kwargs(args=(11,), kwargs={'x': 22})
        {'w': 11, 'x': 22}

        But if you specify `apply_defaults=True` non-specified non-require arguments
        will be returned with their defaults:
        >>> sig.kwargs_from_args_and_kwargs(args=(11,), kwargs={'x': 22}, apply_defaults=True)
        {'w': 11, 'x': 22, 'y': 'YY', 'z': 'ZZ'}

        By default, `ignore_excess=False`, so specifying kwargs that are not in the signature will lead to an exception.
        >>> sig.kwargs_from_args_and_kwargs(args=(11,), kwargs={'x': 22, 'not_in_sig': -1})
        Traceback (most recent call last):
            ...
        TypeError: Got unexpected keyword arguments: not_in_sig

        Specifying `allow_excess=True` will ignore such excess fields of kwargs.
        This is useful when you want to source several functions from a same dict.
        >>> sig.kwargs_from_args_and_kwargs(args=(11,), kwargs={'x': 22, 'not_in_sig': -1}, allow_excess=True)
        {'w': 11, 'x': 22}

        On the other side of `ignore_excess` you have `allow_partial` that will allow you, if
        set to `True`, to underspecify the params of a function (in view of being completed later).
        >>> sig.kwargs_from_args_and_kwargs(args=(), kwargs={'x': 22})
        Traceback (most recent call last):
          ...
        TypeError: missing a required argument: 'w'

        But if you specify `allow_partial=True`...
        >>> sig.kwargs_from_args_and_kwargs(args=(), kwargs={'x': 22}, allow_partial=True)
        {'x': 22}

        That's a lot of control (eight combinations total), but not everything is controllable here:
        Position only and keyword only kinds need to be respected:
        >>> sig.kwargs_from_args_and_kwargs(args=(1, 2, 3, 4), kwargs={})
        Traceback (most recent call last):
          ...
        TypeError: too many positional arguments
        >>> sig.kwargs_from_args_and_kwargs(args=(), kwargs=dict(w=1, x=2, y=3, z=4))
        Traceback (most recent call last):
          ...
        TypeError: 'w' parameter is positional only, but was passed as a keyword

        But if you want to ignore the kind of parameter, just say so:
        >>> sig.kwargs_from_args_and_kwargs(args=(1, 2, 3, 4), kwargs={}, ignore_kind=True)
        {'w': 1, 'x': 2, 'y': 3, 'z': 4}
        >>> sig.kwargs_from_args_and_kwargs(args=(), kwargs=dict(w=1, x=2, y=3, z=4), ignore_kind=True)
        {'w': 1, 'x': 2, 'y': 3, 'z': 4}
        """
        if ignore_kind:
            sig = self.normalize_kind()
        else:
            sig = self

        no_var_kw = not sig.has_var_keyword
        if no_var_kw:  # has no var keyword kinds
            sig_relevant_kwargs = {name: kwargs[name] for name in sig if name in kwargs}  # take only what you need
        else:
            sig_relevant_kwargs = kwargs  # take all the kwargs

        binder = sig.bind_partial if allow_partial else sig.bind
        b = binder(*args, **sig_relevant_kwargs)
        if apply_defaults:
            b.apply_defaults()

        if no_var_kw and not allow_excess:  # don't ignore excess kwargs
            excess = kwargs.keys() - b.arguments
            if excess:
                excess_str = ', '.join(excess)
                raise TypeError(f"Got unexpected keyword arguments: {excess_str}")

        return dict(b.arguments)

    def args_and_kwargs_from_kwargs(self, kwargs,
                                    apply_defaults=False, allow_partial=False, allow_excess=False, ignore_kind=False):
        """Get an (args, kwargs) tuple from the kwargs, where args contain the position only arguments.

        >>> def foo(w, /, x: float, y=1, *, z: int = 1):
        ...     return ((w + x) * y) ** z
        >>> args, kwargs = Sig(foo).args_and_kwargs_from_kwargs(dict(w=4, x=3, y=2, z=1))
        >>> assert (args, kwargs) == ((4,), {'x': 3, 'y': 2, 'z': 1})
        >>> assert foo(*args, **kwargs) == foo(4, 3, 2, z=1) == 14

        See kwargs_from_args_and_kwargs (namely for the description of the arguments.
        """
        position_only_names = {p.name for p in self.parameters.values() if p.kind == PO}
        args = tuple(kwargs[name] for name in position_only_names if name in kwargs)
        # kwargs = self.kwargs_from_args_and_kwargs(args, kwargs, apply_defaults, allow_partial, allow_excess)
        kwargs = {name: kwargs[name] for name in kwargs.keys() - position_only_names}

        kwargs = self.kwargs_from_args_and_kwargs(args, kwargs, apply_defaults=apply_defaults,
                                                  allow_partial=allow_partial, allow_excess=allow_excess,
                                                  ignore_kind=ignore_kind)
        kwargs = {name: kwargs[name] for name in kwargs.keys() - position_only_names}

        return args, kwargs

    def extract_kwargs(self, *args, _ignore_kind=True, _allow_partial=False, _apply_defaults=False, **kwargs):
        """Convenience method that calls kwargs_from_args_and_kwargs with defaults, and ignore_kind=True.

        Strict in the sense that the kwargs cannot contain any arguments that are not
        valid argument names (as per the signature).

        >>> def foo(w, /, x: float, y='YY', *, z: str = 'ZZ'): ...
        >>> sig = Sig(foo)
        >>> assert (
        ...     sig.extract_kwargs(1, 2, 3, z=4)
        ...     == sig.extract_kwargs(1, 2, y=3, z=4)
        ...     == {'w': 1, 'x': 2, 'y': 3, 'z': 4})

        What about var positional and var keywords?
        >>> def bar(*args, **kwargs): ...
        >>> Sig(bar).extract_kwargs(1, 2, y=3, z=4)
        {'args': (1, 2), 'kwargs': {'y': 3, 'z': 4}}

        Note that though `w` is a position only argument, you can specify `w=11` as a keyword argument too (by default):
        >>> Sig(foo).extract_kwargs(w=11, x=22)
        {'w': 11, 'x': 22}

        If you don't want to allow that, you can say `_ignore_kind=False`
        >>> Sig(foo).extract_kwargs(w=11, x=22, _ignore_kind=False)
        Traceback (most recent call last):
          ...
        TypeError: 'w' parameter is positional only, but was passed as a keyword

        You can use `_allow_partial` that will allow you, if
        set to `True`, to underspecify the params of a function (in view of being completed later).
        >>> Sig(foo).extract_kwargs(x=3, y=2)
        Traceback (most recent call last):
          ...
        TypeError: missing a required argument: 'w'

        But if you specify `_allow_partial=True`...
        >>> Sig(foo).extract_kwargs(x=3, y=2, _allow_partial=True)
        {'x': 3, 'y': 2}

        By default, `_apply_defaults=False`, which will lead to only get those arguments you input.
        >>> Sig(foo).extract_kwargs(4, x=3, y=2)
        {'w': 4, 'x': 3, 'y': 2}

        But if you specify `_apply_defaults=True` non-specified non-require arguments
        will be returned with their defaults:
        >>> Sig(foo).extract_kwargs(4, x=3, y=2, _apply_defaults=True)
        {'w': 4, 'x': 3, 'y': 2, 'z': 'ZZ'}
        """
        return self.kwargs_from_args_and_kwargs(
            args, kwargs, apply_defaults=_apply_defaults, allow_partial=_allow_partial, allow_excess=False,
            ignore_kind=_ignore_kind)

    def extract_args_and_kwargs(self, *args, _ignore_kind=True, _allow_partial=False, _apply_defaults=False, **kwargs):
        """Source the (args, kwargs) for the signature instance, ignoring excess arguments.

        >>> def foo(w, /, x: float, y=2, *, z: int = 1):
        ...     return w + x * y ** z
        >>> args, kwargs = Sig(foo).extract_args_and_kwargs(4, x=3, y=2)
        >>> (args, kwargs) == ((4,), {'x': 3, 'y': 2})
        True

        The difference with extract_kwargs is that here the output is ready to be called by the
        function whose signature we have, since the position-only arguments will be returned as
        args.

        >>> foo(*args, **kwargs)
        10

        Note that though `w` is a position only argument, you can specify `w=4` as a keyword argument too (by default):
        >>> args, kwargs = Sig(foo).extract_args_and_kwargs(w=4, x=3, y=2)
        >>> (args, kwargs) == ((4,), {'x': 3, 'y': 2})
        True

        If you don't want to allow that, you can say `_ignore_kind=False`
        >>> Sig(foo).extract_args_and_kwargs(w=4, x=3, y=2, _ignore_kind=False)
        Traceback (most recent call last):
          ...
        TypeError: 'w' parameter is positional only, but was passed as a keyword

        You can use `_allow_partial` that will allow you, if
        set to `True`, to underspecify the params of a function (in view of being completed later).
        >>> Sig(foo).extract_args_and_kwargs(x=3, y=2)
        Traceback (most recent call last):
          ...
        TypeError: missing a required argument: 'w'

        But if you specify `_allow_partial=True`...
        >>> args, kwargs = Sig(foo).extract_args_and_kwargs(x=3, y=2, _allow_partial=True)
        >>> (args, kwargs) == ((), {'x': 3, 'y': 2})
        True

        By default, `_apply_defaults=False`, which will lead to only get those arguments you input.
        >>> args, kwargs = Sig(foo).extract_args_and_kwargs(4, x=3, y=2)
        >>> (args, kwargs) == ((4,), {'x': 3, 'y': 2})
        True

        But if you specify `_apply_defaults=True` non-specified non-require arguments
        will be returned with their defaults:
        >>> args, kwargs = Sig(foo).extract_args_and_kwargs(4, x=3, y=2, _apply_defaults=True)
        >>> (args, kwargs) == ((4,), {'x': 3, 'y': 2, 'z': 1})
        True
        """
        kwargs = self.extract_kwargs(*args, _ignore_kind=_ignore_kind, _allow_partial=_allow_partial,
                                     _apply_defaults=_apply_defaults, **kwargs)
        return self.args_and_kwargs_from_kwargs(kwargs, allow_partial=_allow_partial, apply_defaults=_apply_defaults)

    def source_kwargs(self, *args, _ignore_kind=True, _allow_partial=False, _apply_defaults=False, **kwargs):
        """Source the kwargs for the signature instance, ignoring excess arguments.

        >>> def foo(w, /, x: float, y='YY', *, z: str = 'ZZ'): ...
        >>> Sig(foo).source_kwargs(11, x=22, extra='keywords', are='ignored')
        {'w': 11, 'x': 22}

        Note that though `w` is a position only argument, you can specify `w=11` as a keyword argument too (by default):
        >>> Sig(foo).source_kwargs(w=11, x=22, extra='keywords', are='ignored')
        {'w': 11, 'x': 22}

        If you don't want to allow that, you can say `_ignore_kind=False`
        >>> Sig(foo).source_kwargs(w=11, x=22, extra='keywords', are='ignored', _ignore_kind=False)
        Traceback (most recent call last):
          ...
        TypeError: 'w' parameter is positional only, but was passed as a keyword

        You can use `_allow_partial` that will allow you, if
        set to `True`, to underspecify the params of a function (in view of being completed later).
        >>> Sig(foo).source_kwargs(x=3, y=2, extra='keywords', are='ignored')
        Traceback (most recent call last):
          ...
        TypeError: missing a required argument: 'w'

        But if you specify `_allow_partial=True`...
        >>> Sig(foo).source_kwargs(x=3, y=2, extra='keywords', are='ignored', _allow_partial=True)
        {'x': 3, 'y': 2}

        By default, `_apply_defaults=False`, which will lead to only get those arguments you input.
        >>> Sig(foo).source_kwargs(4, x=3, y=2, extra='keywords', are='ignored')
        {'w': 4, 'x': 3, 'y': 2}

        But if you specify `_apply_defaults=True` non-specified non-require arguments
        will be returned with their defaults:
        >>> Sig(foo).source_kwargs(4, x=3, y=2, extra='keywords', are='ignored', _apply_defaults=True)
        {'w': 4, 'x': 3, 'y': 2, 'z': 'ZZ'}
        """
        return self.kwargs_from_args_and_kwargs(
            args, kwargs, apply_defaults=_apply_defaults, allow_partial=_allow_partial, allow_excess=True,
            ignore_kind=_ignore_kind)

    def source_args_and_kwargs(self, *args, _ignore_kind=True, _allow_partial=False, _apply_defaults=False, **kwargs):
        """Source the (args, kwargs) for the signature instance, ignoring excess arguments.

        >>> def foo(w, /, x: float, y=2, *, z: int = 1):
        ...     return w + x * y ** z
        >>> args, kwargs = Sig(foo).source_args_and_kwargs(4, x=3, y=2, extra='keywords', are='ignored')
        >>> assert (args, kwargs) == ((4,), {'x': 3, 'y': 2})
        >>>

        The difference with source_kwargs is that here the output is ready to be called by the
        function whose signature we have, since the position-only arguments will be returned as
        args.

        >>> foo(*args, **kwargs)
        10

        Note that though `w` is a position only argument, you can specify `w=4` as a keyword argument too (by default):
        >>> args, kwargs = Sig(foo).source_args_and_kwargs(w=4, x=3, y=2, extra='keywords', are='ignored')
        >>> assert (args, kwargs) == ((4,), {'x': 3, 'y': 2})

        If you don't want to allow that, you can say `_ignore_kind=False`
        >>> Sig(foo).source_args_and_kwargs(w=4, x=3, y=2, extra='keywords', are='ignored', _ignore_kind=False)
        Traceback (most recent call last):
          ...
        TypeError: 'w' parameter is positional only, but was passed as a keyword

        You can use `_allow_partial` that will allow you, if
        set to `True`, to underspecify the params of a function (in view of being completed later).
        >>> Sig(foo).source_args_and_kwargs(x=3, y=2, extra='keywords', are='ignored')
        Traceback (most recent call last):
          ...
        TypeError: missing a required argument: 'w'

        But if you specify `_allow_partial=True`...
        >>> args, kwargs = Sig(foo).source_args_and_kwargs(x=3, y=2, extra='keywords', are='ignored', _allow_partial=True)
        >>> (args, kwargs) == ((), {'x': 3, 'y': 2})
        True

        By default, `_apply_defaults=False`, which will lead to only get those arguments you input.
        >>> args, kwargs = Sig(foo).source_args_and_kwargs(4, x=3, y=2, extra='keywords', are='ignored')
        >>> (args, kwargs) == ((4,), {'x': 3, 'y': 2})
        True

        But if you specify `_apply_defaults=True` non-specified non-require arguments
        will be returned with their defaults:
        >>> args, kwargs = Sig(foo).source_args_and_kwargs(4, x=3, y=2, extra='keywords', are='ignored', _apply_defaults=True)
        >>> (args, kwargs) == ((4,), {'x': 3, 'y': 2, 'z': 1})
        True
        """
        kwargs = self.kwargs_from_args_and_kwargs(args, kwargs, allow_excess=True, ignore_kind=_ignore_kind,
                                                  allow_partial=_allow_partial, apply_defaults=_apply_defaults)
        return self.args_and_kwargs_from_kwargs(kwargs, allow_excess=True, ignore_kind=_ignore_kind,
                                                allow_partial=_allow_partial, apply_defaults=_apply_defaults)


########################################################################################################################
# Recipes

def mk_sig_from_args(*args_without_default, **args_with_defaults):
    """Make a Signature instance by specifying args_without_default and args_with_defaults.
    >>> mk_sig_from_args('a', 'b', c=1, d='bar')
    <Signature (a, b, c=1, d='bar')>
    """
    assert all(isinstance(x, str) for x in args_without_default), "all default-less arguments must be strings"
    return Sig.from_objs(*args_without_default, **args_with_defaults).to_simple_signature()


def call_forgivingly(func, *args, **kwargs):
    """Call function on giben args and kwargs, but only taking what the function needs
    (not choking if they're extras variables)"""
    args, kwargs = Sig(func).source_args_and_kwargs(*args, **kwargs)
    return func(*args, **kwargs)


def has_signature(obj):
    return bool(Sig.sig_or_none(obj))


def number_of_required_arguments(obj):
    sig = Sig(obj)
    return len(sig) - len(sig.defaults)


########################################################################################################################
# TODO: Encorporate in Sig
def insert_annotations(s: Signature, *, return_annotation=empty, **annotations):
    """Insert annotations in a signature.
    (Note: not really insert but returns a copy of input signature)
    >>> from inspect import signature
    >>> s = signature(lambda a, b, c=1, d='bar': 0)
    >>> s
    <Signature (a, b, c=1, d='bar')>
    >>> ss = insert_annotations(s, b=int, d=str)
    >>> ss
    <Signature (a, b: int, c=1, d: str = 'bar')>
    >>> insert_annotations(s, b=int, d=str, e=list)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ...
    AssertionError: These argument names weren't found in the signature: {'e'}
    """
    assert set(annotations) <= set(s.parameters), \
        f"These argument names weren't found in the signature: {set(annotations) - set(s.parameters)}"
    params = dict(s.parameters)
    for name, annotation in annotations.items():
        p = params[name]
        params[name] = Parameter(name=name, kind=p.kind, default=p.default, annotation=annotation)
    return Signature(params.values(), return_annotation=return_annotation)


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


def set_signature_of_func(func, parameters, *, return_annotation=empty, __validate_parameters__=True):
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
    sig = Sig(parameters,
              return_annotation=return_annotation,
              __validate_parameters__=__validate_parameters__)
    func.__signature__ = sig.to_simple_signature()
    # Not returning func so it's clear(er) that the function is transformed in place


############# Tools for testing ########################################################################################
from functools import partial


def param_for_kind(name=None, kind='positional_or_keyword', with_default=False, annotation=Parameter.empty):
    """Function to easily and flexibly make inspect.Parameter objects for testing.

    It's annoying to have to compose parameters from scratch to testing things.
    This tool should help making it less annoying.

    >>> from i2.signatures import param_kinds
    >>> list(map(param_for_kind, param_kinds))
    [<Parameter "POSITIONAL_ONLY">, <Parameter "POSITIONAL_OR_KEYWORD">, <Parameter "VAR_POSITIONAL">, <Parameter "KEYWORD_ONLY">, <Parameter "VAR_KEYWORD">]
    >>> param_for_kind.positional_or_keyword()
    <Parameter "POSITIONAL_OR_KEYWORD">
    >>> param_for_kind.positional_or_keyword('foo')
    <Parameter "foo">
    >>> param_for_kind.keyword_only()
    <Parameter "KEYWORD_ONLY">
    >>> param_for_kind.keyword_only('baz', with_default=True)
    <Parameter "baz='dflt_keyword_only'">
    """
    name = name or f"{kind}"
    kind_obj = getattr(Parameter, str(kind).upper())
    kind = str(kind_obj).lower()
    default = f"dflt_{kind}" if with_default and kind not in {'var_positional', 'var_keyword'} else Parameter.empty
    return Parameter(name=name,
                     kind=kind_obj,
                     default=default,
                     annotation=annotation)


param_kinds = list(filter(lambda x: x.upper() == x, Parameter.__dict__))

for kind in param_kinds:
    lower_kind = kind.lower()
    setattr(param_for_kind, lower_kind,
            partial(param_for_kind, kind=kind))
    setattr(param_for_kind, 'with_default',
            partial(param_for_kind, with_default=True))
    setattr(getattr(param_for_kind, lower_kind), 'with_default',
            partial(param_for_kind, kind=kind, with_default=True))
    setattr(getattr(param_for_kind, 'with_default'), lower_kind,
            partial(param_for_kind, kind=kind, with_default=True))


def ch_signature_to_all_pk(sig):
    def changed_params():
        for p in sig.parameters.values():
            if p.kind not in var_param_kinds:
                yield p.replace(kind=PK)
            else:
                yield p

    return Signature(list(changed_params()), return_annotation=sig.return_annotation)
