from functools import wraps

from py2store.base import Store
from py2store.persisters.sql_w_sqlalchemy import SQLAlchemyPersister, SqlDbReader
from py2store.util import lazyprop


class SQLAlchemyStore(Store):
    @wraps(SQLAlchemyPersister.__init__)
    def __init__(self, *args, **kwargs):
        persister = SQLAlchemyPersister(*args, **kwargs)
        super().__init__(persister)


class SQLAlchemyTupleStore(SQLAlchemyStore):
    @lazyprop
    def _key_fields(self):
        return self.store._key_fields

    def _id_of_key(self, k):
        return {field: field_val for field, field_val in zip(self._key_fields, k)}

    def _key_of_id(self, obj):
        return tuple(getattr(obj, x) for x in self._key_fields)

    @lazyprop
    def _data_fields(self):
        return self.store._data_fields

    def _data_of_obj(self, data):
        return {field: field_val for field, field_val in zip(self._data_fields, data)}

    def _obj_of_data(self, obj):
        return tuple(getattr(obj, x) for x in self._data_fields)


# Extras ###############################################################################################################
# Note: The stuff below may require extra dependencies

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    import pandas as pd


    class DfSqlDbReader(SqlDbReader):
        def __getitem__(self, k):
            table = super().__getitem__(k)
            return pd.DataFrame(data=list(table), columns=table.column_names)
