"""
Your portal to many Data Object Layer goodies
"""
import os
from contextlib import suppress

file_sep = os.path.sep


def kvhead(store, n=1):
    """Get the first item of a kv store, or a list of the first n items"""
    if n == 1:
        for k in store:
            return k, store[k]
    else:
        return [(k, store[k]) for i, k in enumerate(store) if i < n]


def ihead(store, n=1):
    """Get the first item of an iterable, or a list of the first n items"""
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
