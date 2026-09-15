# py2store.key_mappers.tuples

Tools to map tuple-structured keys.
That is, converting from any of the following kinds of keys:

> * tuples (or list-like)
> * dicts
> * formatted/templated strings
> * dsv (Delimiter-Separated Values)

### Functions

| `dict_of_str`(d, compiled_regex)                                             |                                                                                          |
|------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `dict_of_tuple`(d, fields)                                                   |                                                                                          |
| [`dsv_of_list`](#py2store.key_mappers.tuples.dsv_of_list)(d[, sep])       | Converting a list of strings to a dsv (delimiter-separated values) string.               |
| [`list_of_dsv`](#py2store.key_mappers.tuples.list_of_dsv)(d[, sep])       | Converting a dsv (delimiter-separated values) string to the list of it's components.     |
| [`mk_obj_of_str`](#py2store.key_mappers.tuples.mk_obj_of_str)(constructor)  | Make a function that transforms a string to an object.                                   |
| [`mk_str_of_obj`](#py2store.key_mappers.tuples.mk_str_of_obj)(attrs)        | Make a function that transforms objects to strings, using specific attributes of object. |
| `str_of_dict`(d, str_format)                                                 |                                                                                          |
| [`str_of_tuple`](#py2store.key_mappers.tuples.str_of_tuple)(d, str_format) | Convert tuple to str.                                                                    |
| `tuple_of_dict`(d, fields)                                                   |                                                                                          |
| `tuple_of_str`(d, compiled_regex)                                            |                                                                                          |

### py2store.key_mappers.tuples.dsv_of_list(d, sep=',')

Converting a list of strings to a dsv (delimiter-separated values) string.

Note that unlike most key mappers, there is no schema imposing size here. If you wish to impose a size
validation, do so externally (we suggest using a decorator for that).

* **Parameters:**
  * **d** – A list of component strings
  * **sep** – The delimiter text used to separate a string into a list of component strings
* **Returns:**
  The delimiter-separated values (dsv) string for the input tuple

```pycon
>>> dsv_of_list(['a', 'brown', 'fox'], sep=' ')
'a brown fox'
>>> dsv_of_list(('jumps', 'over'), sep='/')  # for filepaths (and see that tuple inputs work too!)
'jumps/over'
>>> dsv_of_list(['Sat', 'Jan', '1', '1983'], sep=',')  # csv: the usual delimiter-separated values format
'Sat,Jan,1,1983'
>>> dsv_of_list(['First', 'Last'], sep=':::')  # a longer delimiter
'First:::Last'
>>> dsv_of_list(['singleton'], sep='@')  # when the list has only one element
'singleton'
>>> dsv_of_list([], sep='@')  # when the list is empty
''
```

### py2store.key_mappers.tuples.list_of_dsv(d, sep=',')

Converting a dsv (delimiter-separated values) string to the list of it’s components.

* **Parameters:**
  * **d** – A (delimiter-separated values) string
  * **sep** – The delimiter text used to separate the string into a list of component strings
* **Returns:**
  A list of component strings corresponding to the input delimiter-separated values (dsv) string

```pycon
>>> list_of_dsv('a brown fox', sep=' ')
['a', 'brown', 'fox']
>>> tuple(list_of_dsv('jumps/over', sep='/'))  # for filepaths
('jumps', 'over')
>>> list_of_dsv('Sat,Jan,1,1983', sep=',')  # csv: the usual delimiter-separated values format
['Sat', 'Jan', '1', '1983']
>>> list_of_dsv('First:::Last', sep=':::')  # a longer delimiter
['First', 'Last']
>>> list_of_dsv('singleton', sep='@')  # when the list has only one element
['singleton']
>>> list_of_dsv('', sep='@')  # when the string is empty
[]
```

### py2store.key_mappers.tuples.mk_obj_of_str(constructor)

Make a function that transforms a string to an object. The factory making inverses of what mk_str_from_obj makes.

* **Parameters:**
  **constructor** – The function (or class) that will be used to make objects from the `**kwargs` parsed out of the
  string.
* **Returns:**
  A function factory.

### py2store.key_mappers.tuples.mk_str_of_obj(attrs)

Make a function that transforms objects to strings, using specific attributes of object.

* **Parameters:**
  **attrs** – Attributes that should be read off of the object to make the parameters of the string
* **Returns:**
  A transformation function

```pycon
>>> from dataclasses import dataclass
>>> @dataclass
... class A:
...     foo: int
...     bar: str
>>> a = A(foo=0, bar='rin')
>>> a
A(foo=0, bar='rin')
>>>
>>> str_from_obj = mk_str_of_obj(['foo', 'bar'])
>>> str_from_obj(a, 'ST{foo}/{bar}/G')
'ST0/rin/G'
```

### py2store.key_mappers.tuples.str_of_tuple(d, str_format)

Convert tuple to str.
It’s just `str_format.format(*d)`. Why even write such a function?

1. To have a consistent interface for key conversions
2. We want a KeyValidationError to occur here

* **Parameters:**
  * **d** – tuple if params to str_format
  * **str_format** – Auto fields format string. If you have manual fields, consider auto_field_format_str to convert.
* **Returns:**
  parametrized string

```pycon
>>> str_of_tuple(('hello', 'world'), "Well, {} dear {}!")
'Well, hello dear world!'
```
