# py2store.key_mappers.str_utils

utils from strings

### Functions

| [`args_and_kwargs_indices`](#py2store.key_mappers.str_utils.args_and_kwargs_indices)(format_string)       | Get the sets of indices and names used in manual specification of format strings, or None, None if auto spec.   |
|-----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| [`auto_field_format_str`](#py2store.key_mappers.str_utils.auto_field_format_str)(format_str)            | Get an auto field version of the format_str                                                                     |
| [`compile_str_from_parsed`](#py2store.key_mappers.str_utils.compile_str_from_parsed)(parsed)              | The (quasi-)inverse of string.Formatter.parse.                                                                  |
| `empty_arg_and_kwargs_for_format`(format_string)                                              |                                                                                                                 |
| [`format_params_in_str_format`](#py2store.key_mappers.str_utils.format_params_in_str_format)(format_string)   | Get the "parameter" indices/names of the format_string                                                          |
| [`get_explicit_positions`](#py2store.key_mappers.str_utils.get_explicit_positions)(parsed_str_format)    |                                                                                                                 |
| [`is_automatic_format_params`](#py2store.key_mappers.str_utils.is_automatic_format_params)(format_params)    | Says if the format_params is from an automatic specification                                                    |
| [`is_automatic_format_string`](#py2store.key_mappers.str_utils.is_automatic_format_string)(format_string)    | Says if the format_string is uses automatic specification                                                       |
| [`is_hybrid_format_params`](#py2store.key_mappers.str_utils.is_hybrid_format_params)(format_params)       | Says if the format_params is from a hybrid of auto and manual.                                                  |
| [`is_hybrid_format_string`](#py2store.key_mappers.str_utils.is_hybrid_format_string)(format_string)       | Says if the format_params is from a hybrid of auto and manual.                                                  |
| [`is_manual_format_params`](#py2store.key_mappers.str_utils.is_manual_format_params)(format_params)       | Says if the format_params is from a manual specification                                                        |
| [`is_manual_format_string`](#py2store.key_mappers.str_utils.is_manual_format_string)(format_string)       | Says if the format_string uses a manual specification                                                           |
| [`manual_field_format_str`](#py2store.key_mappers.str_utils.manual_field_format_str)(format_str)          | Get an auto field version of the format_str                                                                     |
| [`n_format_params_in_str_format`](#py2store.key_mappers.str_utils.n_format_params_in_str_format)(format_string) | The number of parameters                                                                                        |
| [`name_fields_in_format_str`](#py2store.key_mappers.str_utils.name_fields_in_format_str)(format_str[, ...]) | Get a manual field version of the format_str                                                                    |
| `parse_str_format`(str_format)                                                                |                                                                                                                 |
| `transform_format_str`(format_str, ...)                                                       |                                                                                                                 |

### py2store.key_mappers.str_utils.args_and_kwargs_indices(format_string)

Get the sets of indices and names used in manual specification of format strings, or None, None if auto spec.

* **Parameters:**
  **format_string** – A format string (i.e. a string with {…} to mark parameter placement and formatting
* **Returns:**
  None, None if format_string is an automatic specification
  set_of_indices_used, set_of_fields_used if it is a manual specification

```pycon
>>> format_string = '{0} (no 1) {2}, {see} this, {0} is a duplicate (appeared before) and {name} is string-named'
>>> assert args_and_kwargs_indices(format_string) == ({0, 2}, {'name', 'see'})
>>> format_string = 'This is a format string with only automatic field specification: {}, {}, {} etc.'
>>> assert args_and_kwargs_indices(format_string) == (set(), set())
```

### py2store.key_mappers.str_utils.auto_field_format_str(format_str)

Get an auto field version of the format_str

* **Parameters:**
  **format_str** – A format string
* **Returns:**
  A transformed format_str that has no names {inside} {formatting} {braces}.

```pycon
>>> auto_field_format_str('R/{0}/{one}/{}/{two}/T')
'R/{}/{}/{}/{}/T'
```

### py2store.key_mappers.str_utils.compile_str_from_parsed(parsed)

The (quasi-)inverse of string.Formatter.parse.

* **Parameters:**
  * **parsed** – iterator of (literal_text, field_name, format_spec, conversion) tuples,
  * **string.Formatter.parse** (*as yield by*)
* **Returns:**
  A format string that would produce such a parsed input.

```pycon
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
```

### py2store.key_mappers.str_utils.format_params_in_str_format(format_string)

Get the “parameter” indices/names of the format_string

* **Parameters:**
  **format_string** – A format string (i.e. a string with {…} to mark parameter placement and formatting
* **Returns:**
  A list of parameter indices used in the format string, in the order they appear, with repetition.
  Parameter indices could be integers, strings, or None (to denote “automatic field numbering”.

```pycon
>>> format_string = '{0} (no 1) {2}, and {0} is a duplicate, {} is unnamed and {name} is string-named'
>>> format_params_in_str_format(format_string)
[0, 2, 0, None, 'name']
```

### py2store.key_mappers.str_utils.get_explicit_positions(parsed_str_format)

```pycon
>>> parsed = parse_str_format("all/{}/is/{2}/position/{except}{this}{0}")
>>> get_explicit_positions(parsed)
{0, 2}
```

### py2store.key_mappers.str_utils.is_automatic_format_params(format_params)

Says if the format_params is from an automatic specification

#### SEE ALSO
is_manual_format_params and is_hybrid_format_params

### py2store.key_mappers.str_utils.is_automatic_format_string(format_string)

Says if the format_string is uses automatic specification

#### SEE ALSO
is_manual_format_params

```pycon
>>> is_automatic_format_string('Manual: indices: {1} {2}, named: {named} {fields}')
False
>>> is_automatic_format_string('Auto: only un-indexed and un-named: {} {}...')
True
>>> is_automatic_format_string('Hybrid: at least a {}, and a {0} or a {name}')
False
>>> is_manual_format_string('No formatting is both manual and automatic formatting!')
True
```

### py2store.key_mappers.str_utils.is_hybrid_format_params(format_params)

Says if the format_params is from a hybrid of auto and manual.

#### NOTE
Hybrid specifications are considered non-valid and can’t be formatted with format_string.format(…).
Yet, it can be useful for flexibility of expression (but will need to be resolved to be used).

#### SEE ALSO
is_manual_format_params and is_automatic_format_params

### py2store.key_mappers.str_utils.is_hybrid_format_string(format_string)

Says if the format_params is from a hybrid of auto and manual.

#### NOTE
Hybrid specifications are considered non-valid and can’t be formatted with format_string.format(…).
Yet, it can be useful for flexibility of expression (but will need to be resolved to be used).

```pycon
>>> is_hybrid_format_string('Manual: indices: {1} {2}, named: {named} {fields}')
False
>>> is_hybrid_format_string('Auto: only un-indexed and un-named: {} {}...')
False
>>> is_hybrid_format_string('Hybrid: at least a {}, and a {0} or a {name}')
True
>>> is_manual_format_string('No formatting is both manual and automatic formatting (so hybrid is both)!')
True
```

### py2store.key_mappers.str_utils.is_manual_format_params(format_params)

Says if the format_params is from a manual specification

#### SEE ALSO
is_automatic_format_params

### py2store.key_mappers.str_utils.is_manual_format_string(format_string)

Says if the format_string uses a manual specification

#### SEE ALSO
is_automatic_format_string and

```pycon
>>> is_manual_format_string('Manual: indices: {1} {2}, named: {named} {fields}')
True
>>> is_manual_format_string('Auto: only un-indexed and un-named: {} {}...')
False
>>> is_manual_format_string('Hybrid: at least a {}, and a {0} or a {name}')
False
>>> is_manual_format_string('No formatting is both manual and automatic formatting!')
True
```

### py2store.key_mappers.str_utils.manual_field_format_str(format_str)

Get an auto field version of the format_str

* **Parameters:**
  **format_str** – A format string
* **Returns:**
  A transformed format_str that has no names {inside} {formatting} {braces}.

```pycon
>>> auto_field_format_str('R/{0}/{one}/{}/{two}/T')
'R/{}/{}/{}/{}/T'
```

### py2store.key_mappers.str_utils.n_format_params_in_str_format(format_string)

The number of parameters

### py2store.key_mappers.str_utils.name_fields_in_format_str(format_str, field_names=None)

Get a manual field version of the format_str

* **Parameters:**
  * **format_str** – A format string
  * **names** – An iterable that produces enough strings to fill all of format_str fields
* **Returns:**
  A transformed format_str

```pycon
>>> name_fields_in_format_str('R/{0}/{one}/{}/{two}/T')
'R/{0}/{1}/{2}/{3}/T'
>>> # Note here that we use the field name to inject a field format as well
>>> name_fields_in_format_str('R/{foo}/{0}/{}/T', ['42', 'hi:03.0f', 'world'])
'R/{42}/{hi:03.0f}/{world}/T'
```
