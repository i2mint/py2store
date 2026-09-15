# py2store.utils.uri_utils

utils to work with URIs

### Functions

| [`build_uri`](#py2store.utils.uri_utils.build_uri)(scheme[, database, username, ...])   | Reverse of `parse_uri` function.            |
|-------------------------------------------------------------------------------------------------|---------------------------------------------|
| `mk_str_making_func`(str_format[, ...])                                                         |                                             |
| [`parse_uri`](#py2store.utils.uri_utils.parse_uri)(uri)                                 | Parses DB URI string into a dict of params. |

### py2store.utils.uri_utils.build_uri(scheme, database='', username=None, password=None, host='localhost', port=None)

Reverse of `parse_uri` function.
Builds a URI string from provided params.

### py2store.utils.uri_utils.parse_uri(uri)

Parses DB URI string into a dict of params.

* **Parameters:**
  **uri** – string formatted as: “scheme://username:password@host:port/database”
* **Returns:**
  a dict with these params parsed.
