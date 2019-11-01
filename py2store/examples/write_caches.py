from py2store.utils.cumul_aggreg_write import join_byte_values_and_key_as_current_utc_milliseconds, \
    CumulAggregWriteWithAutoFlush


def append_and_print_state(store, data):
    store.append(data)
    print(f"Appended [{data}].\tcache: {store.cache},\tstore: {store.store}")


def timestamp_on_store():
    s = CumulAggregWriteWithAutoFlush(store={},
                                      cache_to_kv=join_byte_values_and_key_as_current_utc_milliseconds,
                                      flush_cache_condition=lambda x: len(x) >= 3
                                      )

    append_and_print_state(s, b'Hello')
    append_and_print_state(s, b'World')
    append_and_print_state(s, b'!')
    append_and_print_state(s, b'Wassup?')


def timestamp_on_cache_and_concatenate_all_values():
    """The cache timestamps (with system clock) every item on insertion (append) and uses the min timestamp as
    a key for storage."""
    from collections import UserList
    import time

    class TimestampedItemsCache(UserList):
        def append(self, item):
            ts = time.time()
            super().append((ts, item))

    def min_key_joined_values(items):
        sorted_items = sorted(items, key=lambda x: x[0])
        k = sorted_items[0][0]
        join_char = sorted_items[0][1][0:0]  # better way to get '' or b'' according to data type?
        yield k, join_char.join(x[1] for x in sorted_items)

    s = CumulAggregWriteWithAutoFlush(store={},
                                      cache_to_kv=min_key_joined_values,
                                      flush_cache_condition=lambda x: len(x) >= 3,
                                      mk_cache=TimestampedItemsCache
                                      )

    append_and_print_state(s, b'Hello');
    time.sleep(0.1);
    append_and_print_state(s, b'World');
    time.sleep(0.1);
    append_and_print_state(s, b'!');
    time.sleep(0.1);
    append_and_print_state(s, b'Wassup?');
    time.sleep(0.1);