# py2store.utils.mappify

Utils to wrap any object into a mapping interface

### Functions

| `bracket_getter`(obj, k)                       |    |
|------------------------------------------------|----|
| `dot_str_key_iterator`(p)                      |    |
| `simple_glom`(target, spec[, node_types, ...]) |    |

### Classes

| [`LeafMappify`](#py2store.utils.mappify.LeafMappify)(target[, node_types, ...])         | A dict-like interface to glom.   |
|-------------------------------------------------------------------------------------------------|----------------------------------|
| [`Mappify`](#py2store.utils.mappify.Mappify)(target[, node_types, key_concat, ...]) |                                  |

### *class* py2store.utils.mappify.LeafMappify(target, node_types=(<class 'dict'>, ), key_concat=<function Mappify.<lambda>>, names_of_literals=(), \*\*kwargs)

Bases: [`Mappify`](#py2store.utils.mappify.Mappify)

A dict-like interface to glom. Here, only leaf keys are taken into account.

```pycon
>>> d = {
...     'a': 'simple',
...     'b': {'is': 'nested'},
...     'c': {'is': 'nested', 'and': 'has', 'a': [1, 2, 3]}
... }
>>> g = LeafMappify(d)
>>>
>>> assert list(g) == ['a', 'b.is', 'c.is', 'c.and', 'c.a']
>>> assert g['a'] == 'simple'
>>> assert g['b.is'] == 'nested'
>>> assert g['c.a'] == [1, 2, 3]
>>>
>>> for k, v in g.items():
...     print(f"{k}: {v}")
...
a: simple
b.is: nested
c.is: nested
c.and: has
c.a: [1, 2, 3]
```

### *class* py2store.utils.mappify.Mappify(target, node_types=(<class 'dict'>, ), key_concat=<function Mappify.<lambda>>, names_of_literals=(), \*\*kwargs)

Bases: `KvReader`

```pycon
>>> d = {
...     'a': 'simple',
...     'b': {'is': 'nested'},
...     'c': {'is': 'nested', 'and': 'has', 'a': [1, 2, 3]}
... }
>>> g = Mappify(d)
>>>
>>> assert list(g) == ['a', 'b.is', 'b', 'c.is', 'c.and', 'c.a', 'c']
>>> assert g['a'] == 'simple'
>>> assert g['b.is'] == 'nested'
>>> assert g['c.a'] == [1, 2, 3]
>>>
>>> for k, v in g.items():
...     print(f"{k}: {v}")
...
a: simple
b.is: nested
b: {'is': 'nested'}
c.is: nested
c.and: has
c.a: [1, 2, 3]
c: {'is': 'nested', 'and': 'has', 'a': [1, 2, 3]}
```
