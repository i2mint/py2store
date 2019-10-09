from py2store import QuickBinaryStore
from py2store.mixins import ReadOnlyMixin
# from py2store import Store

from os.path import sep as path_sep


def wrap_kvs(store_cls, name=None, *, key_of_id=None, id_of_key=None, obj_of_data=None, data_of_obj=None):
    if name is not None:
        _store_cls = store_cls
        store_cls = type(name, (_store_cls,), {})  # make a "copy"

    if key_of_id is not None:
        def _key_of_id(self, _id):
            return key_of_id(super(store_cls, self)._key_of_id(_id))

        store_cls._key_of_id = _key_of_id

    if id_of_key is not None:
        def _id_of_key(self, k):
            return super(store_cls, self)._id_of_key(id_of_key(k))

        store_cls._id_of_key = _id_of_key

    if obj_of_data is not None:
        def _obj_of_data(self, _id):
            return obj_of_data(super(store_cls, self)._obj_of_data(_id))

        store_cls._obj_of_data = _obj_of_data

    if data_of_obj is not None:
        def _data_of_obj(self, obj):
            return super(store_cls, self)._data_of_obj(data_of_obj(obj))

        store_cls._data_of_obj = _data_of_obj

    return store_cls
