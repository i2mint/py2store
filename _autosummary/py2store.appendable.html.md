# py2store.appendable

### py2store.appendable(store_cls=None, , item2kv, return_keys=False, \_\_module_\_=None, \_\_name_\_=None, \_\_qualname_\_=None, \_\_doc_\_=None, \_\_annotations_\_=None, \_\_defaults_\_=None, \_\_kwdefaults_\_=None)

Makes a new class with append (and consequential extend) methods

* **Parameters:**
  * **store_cls** – The store class to subclass
  * **item2kv** – The function that produces a (key, val) pair from an item
  * **new_store_name** – The name to give the new class (default will be ‘Appendable’ + store_cls._\_name_\_)
* **Returns:**
  append, and extend.
* **Return type:**
  A subclass of store_cls with two additional methods

```pycon
>>> item_to_kv = lambda item: (item['L'], item)  # use value of 'L' as the key, and value is the item itself
>>> MyStore = appendable(dict, item2kv=item_to_kv)
>>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
[('let', {'L': 'let', 'I': 'it', 'G': 'go'})]
```

Use mk_item2kv.from_item_to_key_params_and_val with tuple key params

```pycon
>>> item_to_kv = appendable.mk_item2kv_for.item_to_key_params_and_val(lambda x: ((x['L'], x['I']), x['G']), '{}/{}')
>>> MyStore = appendable(item2kv=item_to_kv)(dict)  # showing the append(...)(store) form
>>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
[('let/it', 'go')]
```

Use mk_item2kv.from_item_to_key_params_and_val with dict key params

```pycon
>>> item_to_kv = appendable.mk_item2kv_for.item_to_key_params_and_val(
...     lambda x: ({'L': x['L'], 'G': x['G']}, x['I']), '{G}_{L}')
>>> @appendable(item2kv=item_to_kv)  # showing the @ form
... class MyStore(dict):
...     pass
>>> s = MyStore(); s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
[('go_let', 'it')]
```

Use mk_item2kv.fields to get a tuple key from item fields,
defining the sub-dict of the remaining fields to be the value.
Also showing here how you can decorate the instance itself.

```pycon
>>> item_to_kv = appendable.mk_item2kv_for.fields(['G', 'L'], key_as_tuple=True)
>>> d = {}
>>> s = appendable(d, item2kv=item_to_kv)
>>> s.append({'L': 'let', 'I': 'it', 'G': 'go'}); list(s.items())
[(('go', 'let'), {'I': 'it'})]
```

You can make the “append” and “extend” methods to return the new generated keys by
using the “return_keys” flag.

```pycon
>>> d = {}
>>> s = appendable(d, item2kv=item_to_kv, return_keys=True)
>>> s.append({'L': 'let', 'I': 'it', 'G': 'go'})
('go', 'let')
```
