# py2store.utils.mongoquery

Transform mongo-like selector dicts (filters) into boolean functions that implement the condition

Modified from mongoquery ([https://github.com/kapouille/mongoquery](https://github.com/kapouille/mongoquery))

mongoquery provides a straightforward API to match Python objects against
MongoDB Query Language queries.

### Functions

| [`is_non_string_sequence`](#py2store.utils.mongoquery.is_non_string_sequence)(entry)   | Returns True if entry is a Python sequence iterable, and not a string   |
|----------------------------------------------------------------------------------|-------------------------------------------------------------------------|

### Classes

| [`Query`](#py2store.utils.mongoquery.Query)(definition)   | The Query class is used to match an object against a MongoDB-like query   |
|----------------------------------------------------------------------|---------------------------------------------------------------------------|

### Exceptions

| [`QueryError`](#py2store.utils.mongoquery.QueryError)   | Query error exception   |
|---------------------------------------------------------------|-------------------------|

### *class* py2store.utils.mongoquery.Query(definition)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

The Query class is used to match an object against a MongoDB-like query

#### match(entry)

Matches the entry object against the query specified on instanciation

### *exception* py2store.utils.mongoquery.QueryError

Bases: [`Exception`](https://docs.python.org/3/builtins/exceptions.html#Exception)

Query error exception

### py2store.utils.mongoquery.is_non_string_sequence(entry)

Returns True if entry is a Python sequence iterable, and not a string
