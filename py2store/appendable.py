"""Forwards to dol.appendable:

Tools to add append-functionality to key-val stores. The main function is
    `appendable_store_cls = add_append_functionality_to_store_cls(store_cls, item2kv, ...)`
You give it the `store_cls` you want to sub class, and a item -> (key, val) function, and you get a store (subclass) that
has a `store.append(item)` method. Also includes an extend method (that just called appends in a loop.

See add_append_functionality_to_store_cls docs for examples.

"""

from dol.appendable import *
