# py2store.utils.attr_dict

a data object layer for object attributes

### Functions

| [`attr_wrap`](#py2store.utils.attr_dict.attr_wrap)(cls[, name])   | Returns a Mapping class that routes attribute access to keys of mapping.   |
|---------------------------------------------------------------------------|----------------------------------------------------------------------------|
| `special_dir`(self)                                                       |                                                                            |

### Classes

| [`AttrMap`](#py2store.utils.attr_dict.AttrMap)(arg)   | A read-only façade for navigating a JSON-like object using attribute notation.   |
|-----------------------------------------------------------------|----------------------------------------------------------------------------------|

### *class* py2store.utils.attr_dict.AttrMap(arg)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

A read-only façade for navigating a JSON-like object using attribute notation.
Based on Luciano Ramalho’s “Fluent Python” book.

```pycon
>>> t = AttrMap({'a': {'b': 2, 'foo': 'bar'}, 'b': [1,2,3]})
>>> t
AttrMap({'a': {'b': 2, 'foo': 'bar'}, 'b': [1, 2, 3]})
>>> t.a
AttrMap({'b': 2, 'foo': 'bar'})
>>> t.a.foo
'bar'
>>> t.b
[1, 2, 3]
```

#### SEE ALSO
‘AttrDict’ in `dol.sources` module.

### py2store.utils.attr_dict.attr_wrap(cls, name=None)

Returns a Mapping class that routes attribute access to keys of mapping.

```pycon
>>> A = attr_wrap(dict)
>>> t = A({'a_special_attr': 'foo', 'another_attr': 2, # valid identifiers
...        42: [1, 2], '$invalid': 'identifier', 'class': 'is a reserved keyword'})  # not valid identifiers
>>> # verify that we have the attr we want
>>> assert 'a_special_attr' in dir(t)
>>> assert 'another_attr' in dir(t)
>>> # verify that we DO NOT have the attr we DO NOT want
>>> assert 42 not in dir(t)
>>> assert '$invalid' not in dir(t)
>>> assert 'class' not in dir(t)
```

#### SEE ALSO
‘AttrDict’ in `dol.sources` module.

### py2store.utils.attr_dict.iskeyword()

x._\_contains_\_(y) <==> y in x.
