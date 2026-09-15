"""
py2store: tools to create simple and consistent interfaces to complicated and varied data sources.

The core has moved to the ``dol`` package (Data Object Layer); py2store keeps the original
names, re-exports them, and keeps the local-file stores that still live here. A store is a
``MutableMapping`` whose keys and values are transformed on the way in and out, so that files,
zip archives or databases are read and written like a ``dict``.

Main entry points:

- ``LocalTextStore``, ``LocalBinaryStore``, ``LocalPickleStore``, ``LocalJsonStore``: the files under a root directory as a dict
- ``QuickStore``: the pickle store with a temporary default root and directories created on write
- ``wrap_kvs``, ``filt_iter``, ``cached_keys``: transform a store's keys, values or iteration (from ``dol.trans``)
- ``kvhead``, ``ihead``: peek at the first items of a store or an iterable

>>> from py2store import kvhead
>>> kvhead({'a': 1, 'b': 2})
('a', 1)
"""
import os
from contextlib import suppress

file_sep = os.path.sep


def kvhead(store, n=1):
    """Get the first ``(key, value)`` item of a store, or a list of the first ``n`` items.

    With ``n=1`` the item itself is returned (``None`` if the store is empty); otherwise a
    list of at most ``n`` items, in the store's iteration order.

    >>> kvhead({'a': 1, 'b': 2})
    ('a', 1)
    >>> kvhead({'a': 1, 'b': 2}, 5)
    [('a', 1), ('b', 2)]
    >>> kvhead({}) is None
    True
    """
    if n == 1:
        for k in store:
            return k, store[k]
    else:
        return [(k, store[k]) for i, k in enumerate(store) if i < n]


def ihead(store, n=1):
    """Get the first item of an iterable, or a list of the first ``n`` items.

    With ``n=1`` the item itself is returned (``None`` if the iterable is empty); otherwise a
    list of at most ``n`` items.

    >>> ihead(iter('abc'))
    'a'
    >>> ihead('abc', 2)
    ['a', 'b']
    >>> ihead(iter('')) is None
    True
    """
    if n == 1:
        for item in iter(store):
            return item
    else:
        return [item for i, item in enumerate(store) if i < n]


from py2store.util import lazyprop, partialclass, groupby, regroupby, igroupby

from py2store.base import (
    Collection,
    KvReader,
    KvPersister,
    Reader,
    Persister,
    kv_walk,
    Store,
)

from py2store.persisters.local_files import FileReader
from py2store.my.grabbers import ipython_display_val_trans

from py2store.stores.local_store import (
    LocalStore,
    LocalBinaryStore,
    LocalTextStore,
    LocalPickleStore,
    LocalJsonStore,
    PickleStore,  # consider deprecating and use LocalPickleStore instead?
)
from py2store.stores.local_store import (
    QuickStore,
    QuickBinaryStore,
    QuickTextStore,
    QuickJsonStore,
    QuickPickleStore,
)
from py2store.stores.local_store import (
    DirReader,
    DirStore,
)

from py2store.misc import (
    MiscGetter,
    MiscGetterAndSetter,
    misc_objs,
    misc_objs_get,
    get_obj,
    set_obj,
)

from py2store.trans import (
    wrap_kvs,
    disable_delitem,
    disable_setitem,
    mk_read_only,
    kv_wrap,
    cached_keys,
    filt_iter,
    add_path_get,
    insert_aliases,
    add_ipython_key_completions,
    cache_iter,  # being deprecated
)
from py2store.access import (
    user_configs_dict,
    user_configs,
    user_defaults_dict,
    user_defaults,
)
from py2store.caching import (
    WriteBackChainMap,
    mk_cached_store,
    store_cached,
    store_cached_with_single_key,
    ensure_clear_to_kv_store,
    flush_on_exit,
    mk_write_cached_store,
)

from py2store.appendable import appendable

from py2store.slib.s_zipfile import (
    ZipReader,
    ZipFilesReader,
    FilesOfZip,
    FlatZipFilesReader,
    mk_flatzips_store,
    FileStreamsOfZip,
    ZipFileStreamsReader,
)

from py2store.naming import StrTupleDict
from py2store.paths import mk_relative_path_store

###### Optionals... ##############################################################################
# TODO: Look into sanity of suppressing both import and module errors
ignore_if_module_not_found = suppress(ModuleNotFoundError, ImportError)

with ignore_if_module_not_found:
    from py2store.access import myconfigs

with ignore_if_module_not_found:
    from py2store.access import mystores

with ignore_if_module_not_found:
    from py2store.stores.s3_store import (
        S3BinaryStore,
        S3TextStore,
        S3PickleStore,
    )

# If you want it, import from mongodol (pip installable) directly
# with ignore_if_module_not_found:
#     from mongodol.stores import (
#         MongoStore,
#         MongoTupleKeyStore,
#         MongoAnyKeyStore,
#     )

with ignore_if_module_not_found:
    from py2store.persisters.sql_w_sqlalchemy import (
        SqlDbReader,
        SqlTableRowsCollection,
        SqlTableRowsSequence,
        SqlDbCollection,
        SQLAlchemyPersister,
    )
    from py2store.stores.sql_w_sqlalchemy import (
        SQLAlchemyStore,
        SQLAlchemyTupleStore,
    )
