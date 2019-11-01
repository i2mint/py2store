"""
How to run a test of MSSQL instance locally with a Docker container:

docker rm -f mssql-test
docker run -e ACCEPT_EULA=Y -e SA_PASSWORD=password -p 1433:1433 -d --name mssql-test mcr.microsoft.com/mssql/server:2017-CU8-ubuntu
sleep 10
pytest tests/_test_sql_w_odbc_in_progress.py
"""
from py2store.persisters.sql_w_odbc import SQLServerPersister

from tests.base_test import BasePersisterTest

URI = 'tcp://localhost:1433/test_db'


class TestSQLServerPersister(BasePersisterTest):
    db = SQLServerPersister(URI)

    # def _assert_eq(self, obj_from_db, data):
    #     """ Custom comparison by attributes, since persister returns dicts. """
    #     for data_key, data_val in data.items():
    #         val_from_db = obj_from_db[data_key]
    #         assert val_from_db == data_val
