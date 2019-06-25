import inspect
import re
import itertools


def _empty_func():
    pass


def set_signature(signature):
    def decorator(func):
        return wraps(_empty_func, expected=signature)(func)
    return decorator


def get_function_body(func):
    source_lines = inspect.getsourcelines(func)[0]
    source_lines = itertools.dropwhile(lambda x: x.startswith('@'), source_lines)
    line = next(source_lines).strip()
    if not line.startswith('def ') and not line.startswith('class'):
        return line.rsplit(':')[-1].strip()
    elif not line.endswith(':'):
        for line in source_lines:
            line = line.strip()
            if line.endswith(':'):
                break
    # Handle functions that are not one-liners
    first_line = next(source_lines)
    # Find the indentation of the first line
    indentation = len(first_line) - len(first_line.lstrip())
    return ''.join([first_line[indentation:]] + [line[indentation:] for line in source_lines])


class ExistingArgument(ValueError):
    pass


class MissingArgument(ValueError):
    pass


def make_sentinel(name='_MISSING', var_name=None):
    """Creates and returns a new **instance** of a new class, suitable for
    usage as a "sentinel", a kind of singleton often used to indicate
    a value is missing when ``None`` is a valid input.

    Args:
        name (str): Name of the Sentinel
        var_name (str): Set this name to the name of the variable in
            its respective module enable pickleability.

    >>> make_sentinel(var_name='_MISSING')
    _MISSING

    The most common use cases here in boltons are as default values
    for optional function arguments, partly because of its
    less-confusing appearance in automatically generated
    documentation. Sentinels also function well as placeholders in queues
    and linked lists.

    .. note::

      By design, additional calls to ``make_sentinel`` with the same
      values will not produce equivalent objects.

      >>> make_sentinel('TEST') == make_sentinel('TEST')
      False
      >>> type(make_sentinel('TEST')) == type(make_sentinel('TEST'))
      False

    """

    class Sentinel(object):
        def __init__(self):
            self.name = name
            self.var_name = var_name

        def __repr__(self):
            if self.var_name:
                return self.var_name
            return '%s(%r)' % (self.__class__.__name__, self.name)

        if var_name:
            def __reduce__(self):
                return self.var_name

        def __nonzero__(self):
            return False

        __bool__ = __nonzero__

    return Sentinel()


def _indent(text, margin, newline='\n', key=bool):
    "based on boltons.strutils.indent"
    indented_lines = [(margin + line if key(line) else line)
                      for line in text.splitlines()]
    return newline.join(indented_lines)


NO_DEFAULT = make_sentinel(var_name='NO_DEFAULT')


class FunctionBuilder(object):
    """The FunctionBuilder type provides an interface for programmatically
    creating new functions, either based on existing functions or from
    scratch.

    Note: Based on https://boltons.readthedocs.io

    Values are passed in at construction or set as attributes on the
    instance. For creating a new function based of an existing one,
    see the :meth:`~FunctionBuilder.from_func` classmethod. At any
    point, :meth:`~FunctionBuilder.get_func` can be called to get a
    newly compiled function, based on the values configured.

    >>> fb = FunctionBuilder('return_five', doc='returns the integer 5',
    ...                      body='return 5')
    >>> f = fb.get_func()
    >>> f()
    5
    >>> fb.varkw = 'kw'
    >>> f_kw = fb.get_func()
    >>> f_kw(ignored_arg='ignored_val')
    5

    Note that function signatures themselves changed quite a bit in
    Python 3, so several arguments are only applicable to
    FunctionBuilder in Python 3. Except for *name*, all arguments to
    the constructor are keyword arguments.

    Args:
        name (str): Name of the function.
        doc (str): `Docstring`_ for the function, defaults to empty.
        module (str): Name of the module from which this function was
            imported. Defaults to None.
        body (str): String version of the code representing the body
            of the function. Defaults to ``'pass'``, which will result
            in a function which does nothing and returns ``None``.
        args (list): List of argument names, defaults to empty list,
            denoting no arguments.
        varargs (str): Name of the catch-all variable for positional
            arguments. E.g., "args" if the resultant function is to have
            ``*args`` in the signature. Defaults to None.
        varkw (str): Name of the catch-all variable for keyword
            arguments. E.g., "kwargs" if the resultant function is to have
            ``**kwargs`` in the signature. Defaults to None.
        defaults (dict): A mapping of argument names to default values.
        kwonlyargs (list): Argument names which are only valid as
            keyword arguments. **Python 3 only.**
        kwonlydefaults (dict): A mapping, same as normal *defaults*,
            but only for the *kwonlyargs*. **Python 3 only.**
        annotations (dict): Mapping of type hints and so
            forth. **Python 3 only.**
        filename (str): The filename that will appear in
            tracebacks. Defaults to "boltons.funcutils.FunctionBuilder".
        indent (int): Number of spaces with which to indent the
            function *body*. Values less than 1 will result in an error.
        dict (dict): Any other attributes which should be added to the
            functions compiled with this FunctionBuilder.

    All of these arguments are also made available as attributes which
    can be mutated as necessary.

    .. _Docstring: https://en.wikipedia.org/wiki/Docstring#Python

    """

    _argspec_defaults = {'args': list,
                         'varargs': lambda: None,
                         'varkw': lambda: None,
                         'defaults': lambda: None,
                         'kwonlyargs': list,
                         'kwonlydefaults': dict,
                         'annotations': dict}

    @classmethod
    def _argspec_to_dict(cls, f):
        argspec = inspect.getfullargspec(f)
        return dict((attr, getattr(argspec, attr))
                    for attr in cls._argspec_defaults)

    _defaults = {'doc': str,
                 'dict': dict,
                 'is_async': lambda: False,
                 'module': lambda: None,
                 'body': lambda: 'pass',
                 'indent': lambda: 4,
                 'annotations': dict,
                 'filename': lambda: 'py2mint.utils.FunctionBuilder'}

    _defaults.update(_argspec_defaults)

    _compile_count = itertools.count()

    def __init__(self, name, **kw):
        self.name = name
        for a, default_factory in self._defaults.items():
            val = kw.pop(a, None)
            if val is None:
                val = default_factory()
            setattr(self, a, val)

        if kw:
            raise TypeError('unexpected kwargs: %r' % kw.keys())
        return

    # def get_argspec(self):  # TODO

    def get_sig_str(self, with_annotations=True):
        """Return function signature as a string.

        with_annotations is ignored on Python 2.  On Python 3 signature
        will omit annotations if it is set to False.
        """
        if with_annotations:
            annotations = self.annotations
        else:
            annotations = {}
        return inspect.formatargspec(self.args,
                                     self.varargs,
                                     self.varkw,
                                     [],
                                     self.kwonlyargs,
                                     {},
                                     annotations)

    _KWONLY_MARKER = re.compile(r"""
    \*     # a star
    \s*    # followed by any amount of whitespace
    ,      # followed by a comma
    \s*    # followed by any amount of whitespace
    """, re.VERBOSE)

    def get_invocation_str(self):
        kwonly_pairs = None
        formatters = {}
        if self.kwonlyargs:
            kwonly_pairs = dict((arg, arg)
                                for arg in self.kwonlyargs)
            formatters['formatvalue'] = lambda value: '=' + value

        # TODO: Replace with inspect.signature
        sig = inspect.formatargspec(self.args,
                                    self.varargs,
                                    self.varkw,
                                    [],
                                    kwonly_pairs,
                                    kwonly_pairs,
                                    {},
                                    **formatters)
        sig = self._KWONLY_MARKER.sub('', sig)
        return sig[1:-1]

    @classmethod
    def from_func(cls, func):
        """Create a new FunctionBuilder instance based on an existing
        function. The original function will not be stored or
        modified.
        """
        # TODO: copy_body? gonna need a good signature regex.
        # TODO: might worry about __closure__?
        if not callable(func):
            raise TypeError('expected callable object, not %r' % (func,))

        kwargs = {'name': func.__name__,
                  'doc': func.__doc__,
                  'module': func.__module__,
                  'annotations': getattr(func, "__annotations__", {}),
                  'dict': getattr(func, '__dict__', {})}

        kwargs.update(cls._argspec_to_dict(func))

        # _inspect_iscoroutinefunction always False in Py3?
        # _inspect_iscoroutinefunction = lambda func: False
        # if _inspect_iscoroutinefunction(func):
        #     kwargs['is_async'] = True

        return cls(**kwargs)

    def get_func(self, execdict=None, add_source=True, with_dict=True):
        """Compile and return a new function based on the current values of
        the FunctionBuilder.

        Args:
            execdict (dict): The dictionary representing the scope in
                which the compilation should take place. Defaults to an empty
                dict.
            add_source (bool): Whether to add the source used to a
                special ``__source__`` attribute on the resulting
                function. Defaults to True.
            with_dict (bool): Add any custom attributes, if
                applicable. Defaults to True.

        To see an example of usage, see the implementation of
        :func:`~boltons.funcutils.wraps`.
        """
        execdict = execdict or {}
        body = self.body or self._default_body

        tmpl = 'def {name}{sig_str}:'
        tmpl += '\n{body}'

        if self.is_async:
            tmpl = 'async ' + tmpl

        body = _indent(self.body, ' ' * self.indent)

        name = self.name.replace('<', '_').replace('>', '_')  # lambdas
        src = tmpl.format(name=name, sig_str=self.get_sig_str(with_annotations=False),
                          doc=self.doc, body=body)
        self._compile(src, execdict)
        func = execdict[name]

        func.__name__ = self.name
        func.__doc__ = self.doc
        func.__defaults__ = self.defaults
        func.__kwdefaults__ = self.kwonlydefaults
        func.__annotations__ = self.annotations

        if with_dict:
            func.__dict__.update(self.dict)
        func.__module__ = self.module
        # TODO: caller module fallback?

        if add_source:
            func.__source__ = src

        return func

    def get_defaults_dict(self):
        """Get a dictionary of function arguments with defaults and the
        respective values.
        """
        ret = dict(reversed(list(zip(reversed(self.args),
                                     reversed(self.defaults or [])))))
        kwonlydefaults = getattr(self, 'kwonlydefaults', None)
        if kwonlydefaults:
            ret.update(kwonlydefaults)
        return ret

    def get_arg_names(self, only_required=False):
        arg_names = tuple(self.args) + tuple(getattr(self, 'kwonlyargs', ()))
        if only_required:
            defaults_dict = self.get_defaults_dict()
            arg_names = tuple([an for an in arg_names if an not in defaults_dict])
        return arg_names

    def add_arg(self, arg_name, default=NO_DEFAULT, kwonly=False):
        """Add an argument with optional *default* (defaults to
        ``funcutils.NO_DEFAULT``). Pass *kwonly=True* to add a
        keyword-only argument
        """
        if arg_name in self.args:
            raise ExistingArgument('arg %r already in func %s arg list' % (arg_name, self.name))
        if arg_name in self.kwonlyargs:
            raise ExistingArgument('arg %r already in func %s kwonly arg list' % (arg_name, self.name))
        if not kwonly:
            self.args.append(arg_name)
            if default is not NO_DEFAULT:
                self.defaults = (self.defaults or ()) + (default,)
        else:
            self.kwonlyargs.append(arg_name)
            if default is not NO_DEFAULT:
                self.kwonlydefaults[arg_name] = default
        return

    def remove_arg(self, arg_name):
        """Remove an argument from this FunctionBuilder's argument list. The
        resulting function will have one less argument per call to
        this function.

        Args:
            arg_name (str): The name of the argument to remove.

        Raises a :exc:`ValueError` if the argument is not present.

        """
        args = self.args
        d_dict = self.get_defaults_dict()
        try:
            args.remove(arg_name)
        except ValueError:
            try:
                self.kwonlyargs.remove(arg_name)
            except (AttributeError, ValueError):
                # py2, or py3 and missing from both
                exc = MissingArgument('arg %r not found in %s argument list:'
                                      ' %r' % (arg_name, self.name, args))
                exc.arg_name = arg_name
                raise exc
            else:
                self.kwonlydefaults.pop(arg_name, None)
        else:
            d_dict.pop(arg_name, None)
            self.defaults = tuple([d_dict[a] for a in args if a in d_dict])
        return

    def _compile(self, src, execdict):

        filename = ('<%s-%d>'
                    % (self.filename, next(self._compile_count),))
        try:
            code = compile(src, filename, 'single')
            exec(code, execdict)
        except Exception:
            raise
        return execdict


def _parse_wraps_expected(expected):
    # expected takes a pretty powerful argument, it's processed
    # here. admittedly this would be less trouble if I relied on
    # OrderedDict (there's an impl of that in the commit history if
    # you look
    if expected is None:
        expected = []
    elif isinstance(expected, str):
        expected = [(expected, NO_DEFAULT)]

    expected_items = []
    try:
        expected_iter = iter(expected)
    except TypeError as e:
        raise ValueError('"expected" takes string name, sequence of string names,'
                         ' iterable of (name, default) pairs, or a mapping of '
                         ' {name: default}, not %r (got: %r)' % (expected, e))
    for argname in expected_iter:
        if isinstance(argname, str):
            # dict keys and bare strings
            try:
                default = expected[argname]
            except TypeError:
                default = NO_DEFAULT
        else:
            # pairs
            try:
                argname, default = argname
            except (TypeError, ValueError):
                raise ValueError('"expected" takes string name, sequence of string names,'
                                 ' iterable of (name, default) pairs, or a mapping of '
                                 ' {name: default}, not %r')
        if not isinstance(argname, str):
            raise ValueError('all "expected" argnames must be strings, not %r' % (argname,))

        expected_items.append((argname, default))

    return expected_items


def wraps(func, injected=None, expected=None, **kw):
    """Modeled after the built-in :func:`functools.wraps`, this function is
    used to make your decorator's wrapper functions reflect the
    wrapped function's:

      * Name
      * Documentation
      * Module
      * Signature

    The built-in :func:`functools.wraps` copies the first three, but
    does not copy the signature. This version of ``wraps`` can copy
    the inner function's signature exactly, allowing seamless usage
    and :mod:`introspection <inspect>`. Usage is identical to the
    built-in version::

        >>> from boltons.funcutils import wraps
        >>>
        >>> def print_return(func):
        ...     @wraps(func)
        ...     def wrapper(*args, **kwargs):
        ...         ret = func(*args, **kwargs)
        ...         print(ret)
        ...         return ret
        ...     return wrapper
        ...
        >>> @print_return
        ... def example():
        ...     '''docstring'''
        ...     return 'example return value'
        >>>
        >>> val = example()
        example return value
        >>> example.__name__
        'example'
        >>> example.__doc__
        'docstring'

    In addition, the boltons version of wraps supports modifying the
    outer signature based on the inner signature. By passing a list of
    *injected* argument names, those arguments will be removed from
    the outer wrapper's signature, allowing your decorator to provide
    arguments that aren't passed in.

    Args:

        func (function): The callable whose attributes are to be copied.
        injected (list): An optional list of argument names which
            should not appear in the new wrapper's signature.
        expected (list): An optional list of argument names (or (name,
            default) pairs) representing new arguments introduced by
            the wrapper (the opposite of *injected*). See
            :meth:`FunctionBuilder.add_arg()` for more details.
        update_dict (bool): Whether to copy other, non-standard
            attributes of *func* over to the wrapper. Defaults to True.
        inject_to_varkw (bool): Ignore missing arguments when a
            ``**kwargs``-type catch-all is present. Defaults to True.

    For more in-depth wrapping of functions, see the
    :class:`FunctionBuilder` type, on which wraps was built.

    """
    if injected is None:
        injected = []
    elif isinstance(injected, str):
        injected = [injected]
    else:
        injected = list(injected)

    expected_items = _parse_wraps_expected(expected)

    if isinstance(func, (classmethod, staticmethod)):
        raise TypeError('wraps does not support wrapping classmethods and'
                        ' staticmethods, change the order of wrapping to'
                        ' wrap the underlying function: %r'
                        % (getattr(func, '__func__', None),))

    update_dict = kw.pop('update_dict', True)
    inject_to_varkw = kw.pop('inject_to_varkw', True)
    if kw:
        raise TypeError('unexpected kwargs: %r' % kw.keys())

    fb = FunctionBuilder.from_func(func)
    for arg in injected:
        try:
            fb.remove_arg(arg)
        except MissingArgument:
            if inject_to_varkw and fb.varkw is not None:
                continue  # keyword arg will be caught by the varkw
            raise

    for arg, default in expected_items:
        fb.add_arg(arg, default)  # may raise ExistingArgument

    if fb.is_async:
        fb.body = 'return await _call(%s)' % fb.get_invocation_str()
    else:
        fb.body = 'return _call(%s)' % fb.get_invocation_str()

    def wrapper_wrapper(wrapper_func):
        execdict = dict(_call=wrapper_func, _func=func)
        fully_wrapped = fb.get_func(execdict, with_dict=update_dict)
        fully_wrapped.__wrapped__ = func  # ref to the original function (#115)

        return fully_wrapped

    return wrapper_wrapper
