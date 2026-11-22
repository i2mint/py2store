# py2store.utils.uri_utils

utils to work with URIs

### Functions

| [`build_uri`](#py2store.utils.uri_utils.build_uri)(scheme[, database, username, ...])   | Reverse of `parse_uri` function.                                                |
|-------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`mk_str_making_func`](#py2store.utils.uri_utils.mk_str_making_func)(str_format[, ...])          | Make a function (or method, if `method`) that fills the fields of `str_format`. |
| [`parse_uri`](#py2store.utils.uri_utils.parse_uri)(uri)                                 | Parses DB URI string into a dict of params.                                     |

### py2store.utils.uri_utils.build_uri(scheme, database='', username=None, password=None, host='localhost', port=None)

Reverse of `parse_uri` function.
Builds a URI string from provided params.

### py2store.utils.uri_utils.mk_str_making_func(str_format, input_trans=None, method=False, module=None, name=None)

Make a function (or method, if `method`) that fills the fields of `str_format`.

The function takes the fields as positional or keyword arguments (exactly as many as
the format has fields), optionally passing them through `input_trans` first.

```pycon
>>> f = mk_str_making_func('{a}/{b}')
>>> f('x', b='y')
'x/y'
```

### py2store.utils.uri_utils.parse_uri(uri)

Parses DB URI string into a dict of params.

* **Parameters:**
  **uri** – string formatted as: “scheme://username:password@host:port/database”
* **Returns:**
  a dict with these params parsed.
