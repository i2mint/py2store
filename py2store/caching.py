from functools import wraps


def mk_memoizer(cache_store):
    def memoize(method):
        @wraps(method)
        def memoizer(self, k):
            if k not in cache_store:
                val = method(self, k)
                cache_store[k] = val  # cache it
                return val
            else:
                return cache_store[k]

        return memoizer

    return memoize


def mk_cached_store(caching_store, store_cls_you_want_to_cache):
    class CachedStore(store_cls_you_want_to_cache):
        _caching_store = caching_store

        @mk_memoizer(caching_store)
        def __getitem__(self, k):
            return super().__getitem__(k)

    return CachedStore

#
# def mk_cached_s3_store(local_cache_root, rootdir, rel_path_template, s3_resources=None):
#     local_cache = mk_a_nice_local_store(local_cache_root, rel_path_template)
#     rootdir, s3_resources = process_s3_resources(rootdir, s3_resources)
#
#     CachedWfStore = mk_cached_store(local_cache, NicerWfStore)
#
#     return CachedWfStore(
#         persister_class=S3BinaryStore,
#         persister_kwargs=s3_resources,
#         rootdir=rootdir, rel_path_template=rel_path_template,
#         naming_kwargs=DFLT_NAMING_KWARGS)