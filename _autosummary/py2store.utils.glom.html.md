# py2store.utils.glom

*glom is a util to extract stuff from nested structures.*
It’s one of those excellent utils that I’ve written many times, but never got quite right.
Mahmoud Hashemi got it right.

* **BEGIN LICENSE:**

Copyright (c) 2018, Mahmoud Hashemi

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

> * Redistributions of source code must retain the above copyright
>   notice, this list of conditions and the following disclaimer.
> * Redistributions in binary form must reproduce the above
>   copyright notice, this list of conditions and the following
>   disclaimer in the documentation and/or other materials provided
>   with the distribution.
> * The names of the contributors may not be used to endorse or
>   promote products derived from this software without specific
>   prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
“AS IS” AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

* **END LICENSE:**

Now, at the time of writing this, I’ve already transformed it to bend it to my liking.
At some point it may become something else, but I wanted there to be a trace of what my seed was.
Though I can’t promise I’ll maintain the same functionality as I transform this module, here’s
a tutorial on how to use it in it’s original form:

```default
https://glom.readthedocs.io/en/latest/
```

I only took the main (core) module from the glom project.
Here’s the original docs of this glom module.

If there was ever a Python example of “big things come in small
packages”, `glom` might be it.

The `glom` package has one central entrypoint,
`glom.glom()`. Everything else in the package revolves around that
one function.

A couple of conventional terms you’ll see repeated many times below:

* **target** - glom is built to work on any data, so we simply
  refer to the object being accessed as the  *“target”*
* **spec** -  *(aka “glomspec”, short for specification)* The
  accompanying template used to specify the structure of the return
  value.

Now that you know the terms, let’s take a look around glom’s powerful
semantics.

### Functions

| [`glom`](#py2store.utils.glom.glom)(target, spec, \*\*kwargs)    | Access or construct a value from a given *target* based on the specification declared by *spec*.                                                                                       |
|------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`is_iterable`](#py2store.utils.glom.is_iterable)(x)                    | Similar in nature to [`callable()`](https://docs.python.org/3/builtins/functions.html#callable), `is_iterable` returns `True` if an object is iterable, `False` if not.                |
| [`make_sentinel`](#py2store.utils.glom.make_sentinel)([name, var_name])   | Creates and returns a new **instance** of a new class, suitable for usage as a "sentinel", a kind of singleton often used to indicate a value is missing when `None` is a valid input. |
| [`register`](#py2store.utils.glom.register)(target_type, \*\*kwargs) | Register *target_type* so `glom()` will know how to handle instances of that type as targets.                                                                                          |
| [`register_op`](#py2store.utils.glom.register_op)(op_name, \*\*kwargs)  | For extension authors needing to add operations beyond the builtin 'get' and 'iterate' to the default scope.                                                                           |

### Classes

| [`Auto`](#py2store.utils.glom.Auto)([spec])                             | Switch to Auto mode (the default)                                                                                                                                                         |
|-------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`Call`](#py2store.utils.glom.Call)([func, args, kwargs])               | [`Call`](#py2store.utils.glom.Call) specifies when a target should be passed to a function, *func*.                                                                     |
| [`Check`](#py2store.utils.glom.Check)([spec])                            | Check objects are used to make assertions about the target data, and either pass through the data or raise exceptions if there is a problem.                                              |
| [`Coalesce`](#py2store.utils.glom.Coalesce)(\*subspecs, \*\*kwargs)         | Coalesce objects specify fallback behavior for a list of subspecs.                                                                                                                        |
| [`Fill`](#py2store.utils.glom.Fill)([spec])                             | A specifier type which switches to glom into "fill-mode".                                                                                                                                 |
| [`Glommer`](#py2store.utils.glom.Glommer)(\*\*kwargs)                      | All the wholesome goodness that it takes to make glom work.                                                                                                                               |
| [`Inspect`](#py2store.utils.glom.Inspect)(\*a, \*\*kw)                     | The `Inspect` specifier type provides a way to get visibility into glom's evaluation of a specification, enabling debugging of those tricky problems that may arise with unexpected data. |
| [`Invoke`](#py2store.utils.glom.Invoke)(func)                             | Specifier type designed for easy invocation of callables from glom.                                                                                                                       |
| [`Let`](#py2store.utils.glom.Let)(\*\*kw)                              | This specifier type assigns variables to the scope.                                                                                                                                       |
| [`Literal`](#py2store.utils.glom.Literal)(value)                           | Literal objects specify literal values in rare cases when part of the spec should not be interpreted as a glommable subspec.                                                              |
| [`Path`](#py2store.utils.glom.Path)(\*path_parts)                       | Path objects specify explicit paths when the default `'a.b.c'`-style general access syntax won't work or isn't desirable.                                                                 |
| [`Spec`](#py2store.utils.glom.Spec)(spec[, scope])                      | Spec objects serve three purposes, here they are, roughly ordered by utility:                                                                                                             |
| [`TType`](#py2store.utils.glom.TType)()                                  | `T`, short for "target".                                                                                                                                                                  |
| [`TargetRegistry`](#py2store.utils.glom.TargetRegistry)([register_default_types]) | responsible for registration of target types for iteration and attribute walking                                                                                                          |

### Exceptions

| [`CheckError`](#py2store.utils.glom.CheckError)(msgs, check, path)            | This [`GlomError`](#py2store.utils.glom.GlomError) subtype is raised when target data fails to pass a [`Check`](#py2store.utils.glom.Check)'s specified validation.                                        |
|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`CoalesceError`](#py2store.utils.glom.CoalesceError)(coal_obj, skipped, path)   | This [`GlomError`](#py2store.utils.glom.GlomError) subtype is raised from within a [`Coalesce`](#py2store.utils.glom.Coalesce) spec's processing, when none of the subspecs match and no default is provided. |
| [`GlomError`](#py2store.utils.glom.GlomError)                                | The base exception for all the errors that might be raised from [`glom()`](#py2store.utils.glom.glom) processing logic.                                                                                                |
| [`PathAccessError`](#py2store.utils.glom.PathAccessError)(exc, path, part_idx)     | This [`GlomError`](#py2store.utils.glom.GlomError) subtype represents a failure to access an attribute as dictated by the spec.                                                                                             |
| [`UnregisteredTarget`](#py2store.utils.glom.UnregisteredTarget)(op, target_type, ...) | This [`GlomError`](#py2store.utils.glom.GlomError) subtype is raised when a spec calls for an unsupported action on a target type.                                                                                          |

### *class* py2store.utils.glom.Auto(spec=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Switch to Auto mode (the default)

### *class* py2store.utils.glom.Call(func=None, args=None, kwargs=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

[`Call`](#py2store.utils.glom.Call) specifies when a target should be passed to a function,
*func*.

[`Call`](#py2store.utils.glom.Call) is similar to [`partial()`](https://docs.python.org/3/library/functools.html#functools.partial) in that
it is no more powerful than `lambda` or other functions, but
it is designed to be more readable, with a better `repr`.

* **Parameters:**
  **func** (*callable*) – a function or other callable to be called with
  the target

[`Call`](#py2store.utils.glom.Call) combines well with `T` to construct objects. For
instance, to generate a dict and then pass it to a constructor:

```pycon
>>> class ExampleClass(object):
...    def __init__(self, attr):
...        self.attr = attr
...
>>> target = {'attr': 3.14}
>>> glom(target, Call(ExampleClass, kwargs=T)).attr
3.14
```

This does the same as `glom(target, lambda target:
ExampleClass(\*\*target))`, but it’s easy to see which one reads
better.

#### NOTE
`Call` is mostly for functions. Use a `T` object
if you need to call a method.

#### WARNING
[`Call`](#py2store.utils.glom.Call) has a successor with a fuller-featured API, new
in 19.3.0: the [`Invoke`](#py2store.utils.glom.Invoke) specifier type.

#### glomit(target, scope)

run against the current target

### *class* py2store.utils.glom.Check(spec=T, \*\*kwargs)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Check objects are used to make assertions about the target data,
and either pass through the data or raise exceptions if there is a
problem.

If any check condition fails, a `CheckError` is raised.

* **Parameters:**
  * **spec** – a sub-spec to extract the data to which other assertions will
    be checked (defaults to applying checks to the target itself)
  * **type** – a type or sequence of types to be checked for exact match
  * **equal_to** – a value to be checked for equality match (“==”)
  * **validate** – a callable or list of callables, each representing a
    check condition. If one or more return False or raise an
    exception, the Check will fail.
  * **instance_of** – a type or sequence of types to be checked with isinstance()
  * **one_of** – an iterable of values, any of which can match the target (“in”)
  * **default** – an optional default value to replace the value when the check fails
    (if default is not specified, GlomCheckError will be raised)

Aside from *spec*, all arguments are keyword arguments. Each
argument, except for *default*, represent a check
condition. Multiple checks can be passed, and if all check
conditions are left unset, Check defaults to performing a basic
truthy check on the value.

### *exception* py2store.utils.glom.CheckError(msgs, check, path)

Bases: [`GlomError`](#py2store.utils.glom.GlomError)

This [`GlomError`](#py2store.utils.glom.GlomError) subtype is raised when target data fails to
pass a [`Check`](#py2store.utils.glom.Check)’s specified validation.

An uncaught `CheckError` looks like this:

```default
>>> target = {'a': {'b': 'c'}}
>>> glom(target, {'b': ('a.b', Check(type=int))})
Traceback (most recent call last):
...
glom.CheckError: target at path ['a.b'] failed check, got error: "expected type to be 'int', found type 'str'"
```

If the `Check` contains more than one condition, there may be
more than one error message. The string rendition of the
`CheckError` will include all messages.

You can also catch the `CheckError` and programmatically access
messages through the `msgs` attribute on the `CheckError`
instance.

#### NOTE
As of 2018-07-05 (glom v18.2.0), the validation subsystem is
still very new. Exact error message formatting may be enhanced
in future releases.

### *class* py2store.utils.glom.Coalesce(\*subspecs, \*\*kwargs)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Coalesce objects specify fallback behavior for a list of
subspecs.

Subspecs are passed as positional arguments, and keyword arguments
control defaults. Each subspec is evaluated in turn, and if none
match, a [`CoalesceError`](#py2store.utils.glom.CoalesceError) is raised, or a default is returned,
depending on the options used.

#### NOTE
This operation may seem very familar if you have experience with
[SQL](https://en.wikipedia.org/w/index.php?title=Null_(SQL)&oldid=833093792#COALESCE) or even [C# and others](https://en.wikipedia.org/w/index.php?title=Null_coalescing_operator&oldid=839493322#C#).

In practice, this fallback behavior’s simplicity is only surpassed
by its utility:

```pycon
>>> target = {'c': 'd'}
>>> glom(target, Coalesce('a', 'b', 'c'))
'd'
```

glom tries to get `'a'` from `target`, but gets a
KeyError. Rather than raise a `PathAccessError` as usual,
glom *coalesces* into the next subspec, `'b'`. The process
repeats until it gets to `'c'`, which returns our value,
`'d'`. If our value weren’t present, we’d see:

```pycon
>>> target = {}
>>> glom(target, Coalesce('a', 'b'))
Traceback (most recent call last):
...
glom.CoalesceError: no valid values found. Tried ('a', 'b') and got (PathAccessError, PathAccessError) (at path [])
```

Same process, but because `target` is empty, we get a
[`CoalesceError`](#py2store.utils.glom.CoalesceError). If we want to avoid an exception, and we
know which value we want by default, we can set *default*:

```pycon
>>> target = {}
>>> glom(target, Coalesce('a', 'b', 'c'), default='d-fault')
'd-fault'
```

`'a'`, `'b'`, and `'c'` weren’t present so we got `'d-fault'`.

* **Parameters:**
  * **subspecs** – One or more glommable subspecs
  * **default** – A value to return if no subspec results in a valid value
  * **default_factory** – A callable whose result will be returned as a default
  * **skip** – A value, tuple of values, or predicate function
    representing values to ignore
  * **skip_exc** – An exception or tuple of exception types to catch and
    move on to the next subspec. Defaults to [`GlomError`](#py2store.utils.glom.GlomError), the
    parent type of all glom runtime exceptions.

If all subspecs produce skipped values or exceptions, a
[`CoalesceError`](#py2store.utils.glom.CoalesceError) will be raised. For more examples, check out
the tutorial, which makes extensive use of Coalesce.

### *exception* py2store.utils.glom.CoalesceError(coal_obj, skipped, path)

Bases: [`GlomError`](#py2store.utils.glom.GlomError)

This [`GlomError`](#py2store.utils.glom.GlomError) subtype is raised from within a
[`Coalesce`](#py2store.utils.glom.Coalesce) spec’s processing, when none of the subspecs
match and no default is provided.

The exception object itself keeps track of several values which
may be useful for processing:

* **Parameters:**
  * **coal_obj** ([*Coalesce*](#py2store.utils.glom.Coalesce)) – The original failing spec, see
    [`Coalesce`](#py2store.utils.glom.Coalesce)’s docs for details.
  * **skipped** ([*list*](https://docs.python.org/3/builtins/stdtypes.html#list)) – A list of ignored values and exceptions, in the
    order that their respective subspecs appear in the original
    *coal_obj*.
  * **path** – Like many GlomErrors, this exception knows the path at
    which it occurred.

```pycon
>>> target = {}
>>> glom(target, Coalesce('a', 'b'))
Traceback (most recent call last):
...
glom.CoalesceError: no valid values found. Tried ('a', 'b') and got (PathAccessError, PathAccessError) ...
```

### *class* py2store.utils.glom.Fill(spec=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A specifier type which switches to glom into “fill-mode”. For the
spec contained within the Fill, glom will only interpret explicit
specifier types (including T objects). Whereas the default mode
has special interpretations for each of these builtins, fill-mode
takes a lighter touch, making Fill great for “filling out” Python
literals, like tuples, dicts, sets, and lists.

```pycon
>>> target = {'data': [0, 2, 4]}
>>> spec = Fill((T['data'][2], T['data'][0]))
>>> glom(target, spec)
(4, 0)
```

As you can see, glom’s usual built-in tuple item chaining behavior
has switched into a simple tuple constructor.

(Sidenote for Lisp fans: Fill is like glom’s quasi-quoting.)

### *exception* py2store.utils.glom.GlomError

Bases: [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

The base exception for all the errors that might be raised from
[`glom()`](#py2store.utils.glom.glom) processing logic.

By default, exceptions raised from within functions passed to glom
(e.g., `len`, `sum`, any `lambda`) will not be wrapped in a
GlomError.

### *class* py2store.utils.glom.Glommer(\*\*kwargs)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

All the wholesome goodness that it takes to make glom work. This
type mostly serves to encapsulate the type registration context so
that advanced uses of glom don’t need to worry about stepping on
each other’s toes.

Glommer objects are lightweight and, once instantiated, provide
the [`glom()`](#py2store.utils.glom.glom) method we know and love:

```pycon
>>> glommer = Glommer()
>>> glommer.glom({}, 'a.b.c', default='d')
'd'
>>> Glommer().glom({'vals': list(range(3))}, ('vals', len))
3
```

Instances also provide [`register()`](#py2store.utils.glom.Glommer.register) method for
localized control over type handling.

* **Parameters:**
  **register_default_types** ([*bool*](https://docs.python.org/3/builtins/functions.html#bool)) – Whether or not to enable the
  handling behaviors of the default [`glom()`](#py2store.utils.glom.glom). These
  default actions include dict access, list and iterable
  iteration, and generic object attribute access. Defaults to
  True.

#### register(target_type, \*\*kwargs)

Register *target_type* so `glom()` will
know how to handle instances of that type as targets.

* **Parameters:**
  * **target_type** ([*type*](https://docs.python.org/3/builtins/functions.html#type)) – A type expected to appear in a glom()
    call target
  * **get** (*callable*) – A function which takes a target object and
    a name, acting as a default accessor. Defaults to
    [`getattr()`](https://docs.python.org/3/builtins/functions.html#getattr).
  * **iterate** (*callable*) – A function which takes a target object
    and returns an iterator. Defaults to [`iter()`](https://docs.python.org/3/builtins/functions.html#iter) if
    *target_type* appears to be iterable.
  * **exact** ([*bool*](https://docs.python.org/3/builtins/functions.html#bool)) – Whether or not to match instances of subtypes
    of *target_type*.

#### NOTE
The module-level [`register()`](#py2store.utils.glom.register) function affects the
module-level [`glom()`](#py2store.utils.glom.glom) function’s behavior. If this
global effect is undesirable for your application, or
you’re implementing a library, consider instantiating a
[`Glommer`](#py2store.utils.glom.Glommer) instance, and using the
[`register()`](#py2store.utils.glom.Glommer.register) and `Glommer.glom()`
methods instead.

### *class* py2store.utils.glom.Inspect(\*a, \*\*kw)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The `Inspect` specifier type provides a way to get
visibility into glom’s evaluation of a specification, enabling
debugging of those tricky problems that may arise with unexpected
data.

`Inspect` can be inserted into an existing spec in one of two
ways. First, as a wrapper around the spec in question, or second,
as an argument-less placeholder wherever a spec could be.

`Inspect` supports several modes, controlled by
keyword arguments. Its default, no-argument mode, simply echos the
state of the glom at the point where it appears:

```pycon
>>> target = {'a': {'b': {}}}
>>> val = glom(target, Inspect('a.b'))  # wrapping a spec
---
path:   ['a.b']
target: {'a': {'b': {}}}
output: {}
---
```

Debugging behavior aside, `Inspect` has no effect on
values in the target, spec, or result.

* **Parameters:**
  * **echo** ([*bool*](https://docs.python.org/3/builtins/functions.html#bool)) – Whether to print the path, target, and output of
    each inspected glom. Defaults to True.
  * **recursive** ([*bool*](https://docs.python.org/3/builtins/functions.html#bool)) – Whether or not the Inspect should be applied
    at every level, at or below the spec that it wraps. Defaults
    to False.
  * **breakpoint** ([*bool*](https://docs.python.org/3/builtins/functions.html#bool)) – This flag controls whether a debugging prompt
    should appear before evaluating each inspected spec. Can also
    take a callable. Defaults to False.
  * **post_mortem** ([*bool*](https://docs.python.org/3/builtins/functions.html#bool)) – This flag controls whether exceptions
    should be caught and interactively debugged with [`pdb`](https://docs.python.org/3/library/pdb.html#module-pdb) on
    inspected specs.

All arguments above are keyword-only to avoid overlap with a
wrapped spec.

#### NOTE
Just like `pdb.set_trace()`, be careful about leaving stray
`Inspect()` instances in production glom specs.

### *class* py2store.utils.glom.Invoke(func)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Specifier type designed for easy invocation of callables from glom.

* **Parameters:**
  **func** (*callable*) – A function or other callable object.

`Invoke` is similar to [`functools.partial()`](https://docs.python.org/3/library/functools.html#functools.partial), but with the
ability to set up a “templated” call which interleaves constants and
glom specs.

For example, the following creates a spec which can be used to
check if targets are integers:

```pycon
>>> is_int = Invoke(isinstance).specs(T).constants(int)
>>> glom(5, is_int)
True
```

And this composes like any other glom spec:

```pycon
>>> target = [7, object(), 9]
>>> glom(target, [is_int])
[True, False, True]
```

Another example, mixing positional and keyword arguments:

```pycon
>>> spec = Invoke(sorted).specs(T).constants(key=int, reverse=True)
>>> target = ['10', '5', '20', '1']
>>> glom(target, spec)
['20', '10', '5', '1']
```

Invoke also helps with evaluating zero-argument functions:

```pycon
>>> glom(target={}, spec=Invoke(int))
0
```

(A trivial example, but from timestamps to UUIDs, zero-arg calls do come up!)

#### NOTE
`Invoke` is mostly for functions, object construction, and callable
objects. For calling methods, consider the `T` object.

#### constants(\*a, \*\*kw)

Returns a new [`Invoke`](#py2store.utils.glom.Invoke) spec, with the provided positional
and keyword argument values stored for passing to the
underlying function.

```pycon
>>> spec = Invoke(T).constants(5)
>>> glom(range, (spec, list))
[0, 1, 2, 3, 4]
```

Subsequent positional arguments are appended:

```pycon
>>> spec = Invoke(T).constants(2).constants(10, 2)
>>> glom(range, (spec, list))
[2, 4, 6, 8]
```

Keyword arguments also work as one might expect:

```pycon
>>> round_2 = Invoke(round).constants(ndigits=2).specs(T)
>>> glom(3.14159, round_2)
3.14
```

[`constants()`](#py2store.utils.glom.Invoke.constants) and other [`Invoke`](#py2store.utils.glom.Invoke)
methods may be called multiple times, just remember that every
call returns a new spec.

#### *classmethod* specfunc(spec)

Creates an [`Invoke`](#py2store.utils.glom.Invoke) instance where the function is
indicated by a spec.

```pycon
>>> spec = Invoke.specfunc('func').constants(5)
>>> glom({'func': range}, (spec, list))
[0, 1, 2, 3, 4]
```

#### specs(\*a, \*\*kw)

Returns a new [`Invoke`](#py2store.utils.glom.Invoke) spec, with the provided positional
and keyword arguments stored to be interpreted as specs, with
the results passed to the underlying function.

```pycon
>>> spec = Invoke(range).specs('value')
>>> glom({'value': 5}, (spec, list))
[0, 1, 2, 3, 4]
```

Subsequent positional arguments are appended:

```pycon
>>> spec = Invoke(range).specs('start').specs('end', 'step')
>>> target = {'start': 2, 'end': 10, 'step': 2}
>>> glom(target, (spec, list))
[2, 4, 6, 8]
```

Keyword arguments also work as one might expect:

```pycon
>>> multiply = lambda x, y: x * y
>>> times_3 = Invoke(multiply).constants(y=3).specs(x='value')
>>> glom({'value': 5}, times_3)
15
```

[`specs()`](#py2store.utils.glom.Invoke.specs) and other [`Invoke`](#py2store.utils.glom.Invoke)
methods may be called multiple times, just remember that every
call returns a new spec.

#### star(args=None, kwargs=None)

Returns a new [`Invoke`](#py2store.utils.glom.Invoke) spec, with *args* and/or *kwargs*
specs set to be “starred” or “star-starred” (respectively)

```pycon
>>> import os.path
>>> spec = Invoke(os.path.join).star(args='path')
>>> target = {'path': ['path', 'to', 'dir']}
>>> glom(target, spec)
'path/to/dir'
```

* **Parameters:**
  * **args** (*spec*) – A spec to be evaluated and “starred” into the
    underlying function.
  * **kwargs** (*spec*) – A spec to be evaluated and “star-starred” into
    the underlying function.

One or both of the above arguments should be set.

The [`star()`](#py2store.utils.glom.Invoke.star), like other [`Invoke`](#py2store.utils.glom.Invoke)
methods, may be called multiple times. The *args* and *kwargs*
will be stacked in the order in which they are provided.

### *class* py2store.utils.glom.Let(\*\*kw)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

This specifier type assigns variables to the scope.

```pycon
>>> target = {'data': {'val': 9}}
>>> spec = (Let(value=T['data']['val']), {'val': S['value']})
>>> glom(target, spec)
{'val': 9}
```

### *class* py2store.utils.glom.Literal(value)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Literal objects specify literal values in rare cases when part of
the spec should not be interpreted as a glommable
subspec. Wherever a Literal object is encountered in a spec, it is
replaced with its wrapped *value* in the output.

```pycon
>>> target = {'a': {'b': 'c'}}
>>> spec = {'a': 'a.b', 'readability': Literal('counts')}
>>> pprint(glom(target, spec))
{'a': 'c', 'readability': 'counts'}
```

Instead of accessing `'counts'` as a key like it did with
`'a.b'`, `glom()` just unwrapped the literal and
included the value.

`Literal` takes one argument, the literal value that should appear
in the glom output.

This could also be achieved with a callable, e.g., `lambda x:
'literal_string'` in the spec, but using a `Literal`
object adds explicitness, code clarity, and a clean [`repr()`](https://docs.python.org/3/builtins/functions.html#repr).

### *class* py2store.utils.glom.Path(\*path_parts)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Path objects specify explicit paths when the default
`'a.b.c'`-style general access syntax won’t work or isn’t
desirable. Use this to wrap ints, datetimes, and other valid
keys, as well as strings with dots that shouldn’t be expanded.

```pycon
>>> target = {'a': {'b': 'c', 'd.e': 'f', 2: 3}}
>>> glom(target, Path('a', 2))
3
>>> glom(target, Path('a', 'd.e'))
'f'
```

Paths can be used to join together other Path objects, as
well as `T` objects:

```pycon
>>> Path(T['a'], T['b'])
T['a']['b']
>>> Path(Path('a', 'b'), Path('c', 'd'))
Path('a', 'b', 'c', 'd')
```

Paths also support indexing and slicing, with each access
returning a new Path object:

```pycon
>>> path = Path('a', 'b', 1, 2)
>>> path[0]
Path('a')
>>> path[-2:]
Path(1, 2)
```

#### from_t()

return the same path but starting from T

#### *classmethod* from_text(text)

Make a Path from .-delimited text:

```pycon
>>> Path.from_text('a.b.c')
Path('a', 'b', 'c')
```

#### items()

Returns a tuple of (operation, value) pairs.

```pycon
>>> Path(T.a.b, 'c', T['d']).items()
(('.', 'a'), ('.', 'b'), ('P', 'c'), ('[', 'd'))
```

#### values()

Returns a tuple of values referenced in this path.

```pycon
>>> Path(T.a.b, 'c', T['d']).values()
('a', 'b', 'c', 'd')
```

### *exception* py2store.utils.glom.PathAccessError(exc, path, part_idx)

Bases: [`AttributeError`](https://docs.python.org/3/builtins/exceptions.html#AttributeError), [`KeyError`](https://docs.python.org/3/builtins/exceptions.html#KeyError), [`IndexError`](https://docs.python.org/3/builtins/exceptions.html#IndexError), [`GlomError`](#py2store.utils.glom.GlomError)

This [`GlomError`](#py2store.utils.glom.GlomError) subtype represents a failure to access an
attribute as dictated by the spec. The most commonly-seen error
when using glom, it maintains a copy of the original exception and
produces a readable error message for easy debugging.

If you see this error, you may want to:

> * Check the target data is accurate using `Inspect`
> * Catch the exception and return a semantically meaningful error message
> * Use `glom.Coalesce` to specify a default
> * Use the top-level `default` kwarg on `glom()`

In any case, be glad you got this error and not the one it was
wrapping!

* **Parameters:**
  * **exc** ([*Exception*](https://docs.python.org/3/builtins/exceptions.html#Exception)) – The error that arose when we tried to access
    *path*. Typically an instance of KeyError, AttributeError,
    IndexError, or TypeError, and sometimes others.
  * **path** ([*Path*](#py2store.utils.glom.Path)) – The full Path glom was in the middle of accessing
    when the error occurred.
  * **part_idx** ([*int*](https://docs.python.org/3/builtins/functions.html#int)) – The index of the part of the *path* that caused
    the error.

```pycon
>>> target = {'a': {'b': None}}
>>> glom(target, 'a.b.c')
Traceback (most recent call last):
...
glom.PathAccessError: could not access 'c', part 2 of Path('a', 'b', 'c'), got error: ...
```

### *class* py2store.utils.glom.Spec(spec, scope=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Spec objects serve three purposes, here they are, roughly ordered
by utility:

> 1. As a form of compiled or “curried” glom call, similar to
>    Python’s built-in [`re.compile()`](https://docs.python.org/3/library/re.html#re.compile).
> 2. A marker as an object as representing a spec rather than a
>    literal value in certain cases where that might be ambiguous.
> 3. A way to update the scope within another Spec.

In the second usage, Spec objects are the complement to
`Literal`, wrapping a value and marking that it
should be interpreted as a glom spec, rather than a literal value.
This is useful in places where it would be interpreted as a value
by default. (Such as T[key], Call(func) where key and func are
assumed to be literal values and not specs.)

* **Parameters:**
  * **spec** – The glom spec.
  * **scope** ([*dict*](https://docs.python.org/3/builtins/stdtypes.html#dict)) – additional values to add to the scope when
    evaluating this Spec

### *class* py2store.utils.glom.TType

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

`T`, short for “target”. A singleton object that enables
object-oriented expression of a glom specification.

#### NOTE
`T` is a singleton, and does not need to be constructed.

Basically, think of `T` as your data’s stunt double. Everything
that you do to `T` will be recorded and executed during the
[`glom()`](#py2store.utils.glom.glom) call. Take this example:

```pycon
>>> spec = T['a']['b']['c']
>>> target = {'a': {'b': {'c': 'd'}}}
>>> glom(target, spec)
'd'
```

So far, we’ve relied on the `'a.b.c'`-style shorthand for
access, or used the `Path` objects, but if you want
to explicitly do attribute and key lookups, look no further than
`T`.

But T doesn’t stop with unambiguous access. You can also call
methods and perform almost any action you would with a normal
object:

```pycon
>>> spec = ('a', (T['b'].items(), list))  # reviewed below
>>> glom(target, spec)
[('c', 'd')]
```

A `T` object can go anywhere in the spec. As seen in the example
above, we access `'a'`, use a `T` to get `'b'` and iterate
over its `items`, turning them into a `list`.

You can even use `T` with `Call` to construct objects:

```pycon
>>> class ExampleClass(object):
...    def __init__(self, attr):
...        self.attr = attr
...
>>> target = {'attr': 3.14}
>>> glom(target, Call(ExampleClass, kwargs=T)).attr
3.14
```

On a further note, while `lambda` works great in glom specs, and
can be very handy at times, `T` and `Call`
eliminate the need for the vast majority of `lambda` usage with
glom.

Unlike `lambda` and other functions, `T` roundtrips
beautifully and transparently:

```pycon
>>> T['a'].b['c']('success')
T['a'].b['c']('success')
```

`T`-related access errors raise a `PathAccessError`
during the `glom()` call.

#### NOTE
While `T` is clearly useful, powerful, and here to stay, its
semantics are still being refined. Currently, operations beyond
method calls and attribute/item access are considered
experimental and should not be relied upon.

### *class* py2store.utils.glom.TargetRegistry(register_default_types=True)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

responsible for registration of target types for iteration
and attribute walking

#### get_handler(op, obj, path=None, raise_exc=True)

for an operation and object **instance**, obj, return the
closest-matching handler function, raising UnregisteredTarget
if no handler can be found for *obj* (or False if
raise_exc=False)

#### register_op(op_name, auto_func=None, exact=False)

add operations beyond the builtins (‘get’ and ‘iterate’ at the time
of writing).

auto_func is a function that when passed a type, returns a
handler associated with op_name if it’s supported, or False if
it’s not.

See glom.core.register_op() for the global version used by
extensions.

### *exception* py2store.utils.glom.UnregisteredTarget(op, target_type, type_map, path)

Bases: [`GlomError`](#py2store.utils.glom.GlomError)

This [`GlomError`](#py2store.utils.glom.GlomError) subtype is raised when a spec calls for an
unsupported action on a target type. For instance, trying to
iterate on an non-iterable target:

```pycon
>>> glom(object(), ['a.b.c'])
Traceback (most recent call last):
...
glom.UnregisteredTarget: target type 'object' not registered for 'iterate', expected one of registered types: (...)
```

It should be noted that this is a pretty uncommon occurrence in
production glom usage. See the setup-and-registration
section for details on how to avoid this error.

An UnregisteredTarget takes and tracks a few values:

* **Parameters:**
  * **op** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str)) – The name of the operation being performed (‘get’ or ‘iterate’)
  * **target_type** ([*type*](https://docs.python.org/3/builtins/functions.html#type)) – The type of the target being processed.
  * **type_map** ([*dict*](https://docs.python.org/3/builtins/stdtypes.html#dict)) – A mapping of target types that do support this operation
  * **path** – The path at which the error occurred.

### py2store.utils.glom.glom(target, spec, \*\*kwargs)

Access or construct a value from a given *target* based on the
specification declared by *spec*.

Accessing nested data, aka deep-get:

```pycon
>>> target = {'a': {'b': 'c'}}
>>> glom(target, 'a.b')
'c'
```

Here the *spec* was just a string denoting a path,
`'a.b.`. As simple as it should be. The next example shows
how to use nested data to access many fields at once, and make
a new nested structure.

Constructing, or restructuring more-complicated nested data:

```pycon
>>> target = {'a': {'b': 'c', 'd': 'e'}, 'f': 'g', 'h': [0, 1, 2]}
>>> spec = {'a': 'a.b', 'd': 'a.d', 'h': ('h', [lambda x: x * 2])}
>>> output = glom(target, spec)
>>> pprint(output)
{'a': 'c', 'd': 'e', 'h': [0, 2, 4]}
```

`glom` also takes a keyword-argument, *default*. When set,
if a `glom` operation fails with a [`GlomError`](#py2store.utils.glom.GlomError), the
*default* will be returned, very much like
[`dict.get()`](https://docs.python.org/3/builtins/stdtypes.html#dict.get):

```pycon
>>> glom(target, 'a.xx', default='nada')
'nada'
```

The *skip_exc* keyword argument controls which errors should
be ignored.

```pycon
>>> glom({}, lambda x: 100.0 / len(x), default=0.0, skip_exc=ZeroDivisionError)
0.0
```

* **Parameters:**
  * **target** ([*object*](https://docs.python.org/3/builtins/functions.html#object)) – the object on which the glom will operate.
  * **spec** ([*object*](https://docs.python.org/3/builtins/functions.html#object)) – Specification of the output object in the form
    of a dict, list, tuple, string, other glom construct, or
    any composition of these.
  * **default** ([*object*](https://docs.python.org/3/builtins/functions.html#object)) – An optional default to return in the case
    an exception, specified by *skip_exc*, is raised.
  * **skip_exc** ([*Exception*](https://docs.python.org/3/builtins/exceptions.html#Exception)) – An optional exception or tuple of
    exceptions to ignore and return *default* (None if
    omitted). If *skip_exc* and *default* are both not set,
    glom raises errors through.
  * **scope** ([*dict*](https://docs.python.org/3/builtins/stdtypes.html#dict)) – Additional data that can be accessed
    via S inside the glom-spec.

It’s a small API with big functionality, and glom’s power is
only surpassed by its intuitiveness. Give it a whirl!

### py2store.utils.glom.is_iterable(x)

Similar in nature to [`callable()`](https://docs.python.org/3/builtins/functions.html#callable), `is_iterable` returns
`True` if an object is iterable, `False` if not.

```pycon
>>> is_iterable([])
True
>>> is_iterable(1)
False
```

### py2store.utils.glom.make_sentinel(name='_MISSING', var_name=None)

Creates and returns a new **instance** of a new class, suitable for
usage as a “sentinel”, a kind of singleton often used to indicate
a value is missing when `None` is a valid input.

* **Parameters:**
  * **name** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the Sentinel
  * **var_name** ([*str*](https://docs.python.org/3/builtins/stdtypes.html#str)) – Set this name to the name of the variable in
    its respective module enable pickleability.

```pycon
>>> make_sentinel(var_name='_MISSING')
_MISSING
```

The most common use cases here in boltons are as default values
for optional function arguments, partly because of its
less-confusing appearance in automatically generated
documentation. Sentinels also function well as placeholders in queues
and linked lists.

#### NOTE
By design, additional calls to `make_sentinel` with the same
values will not produce equivalent objects.

```pycon
>>> make_sentinel('TEST') == make_sentinel('TEST')
False
>>> type(make_sentinel('TEST')) == type(make_sentinel('TEST'))
False
```

### py2store.utils.glom.register(target_type, \*\*kwargs)

Register *target_type* so `glom()` will
know how to handle instances of that type as targets.

* **Parameters:**
  * **target_type** ([*type*](https://docs.python.org/3/builtins/functions.html#type)) – A type expected to appear in a glom()
    call target
  * **get** (*callable*) – A function which takes a target object and
    a name, acting as a default accessor. Defaults to
    [`getattr()`](https://docs.python.org/3/builtins/functions.html#getattr).
  * **iterate** (*callable*) – A function which takes a target object
    and returns an iterator. Defaults to [`iter()`](https://docs.python.org/3/builtins/functions.html#iter) if
    *target_type* appears to be iterable.
  * **exact** ([*bool*](https://docs.python.org/3/builtins/functions.html#bool)) – Whether or not to match instances of subtypes
    of *target_type*.

#### NOTE
The module-level [`register()`](#py2store.utils.glom.register) function affects the
module-level [`glom()`](#py2store.utils.glom.glom) function’s behavior. If this
global effect is undesirable for your application, or
you’re implementing a library, consider instantiating a
[`Glommer`](#py2store.utils.glom.Glommer) instance, and using the
[`register()`](#py2store.utils.glom.Glommer.register) and `Glommer.glom()`
methods instead.

### py2store.utils.glom.register_op(op_name, \*\*kwargs)

For extension authors needing to add operations beyond the builtin
‘get’ and ‘iterate’ to the default scope. See TargetRegistry for more details.
