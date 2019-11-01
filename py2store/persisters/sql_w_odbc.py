import platform
import subprocess
from collections.abc import MutableMapping

from py2store.util import ModuleNotFoundErrorNiceMessage
from py2store.utils.uri_parsing import parse_uri, build_uri

with ModuleNotFoundErrorNiceMessage():
    import pyodbc


class SQLServerPersister(MutableMapping):
    def __init__(self, uri, collection='py2store_default_table', primary_key='id', data_fields=('name',)):
        """
        :param uri: Uniform Resource Identifier of a database you would like to use.
                tcp://user:password@localhost:1433/my_db
                    or
                user:password@localhost:1433/my_db
                    or even just
                user:password/my_db

        :param collection: name of the table to use, i.e. "my_table".
        :param primary_key: primary key column name.
        :param data_fields: data columns names.
        """
        self.__check_dependencies()

        uri_parsed = parse_uri(uri)
        self._sql_server_client = pyodbc.connect(
            'DRIVER={{ODBC Driver 17 for SQL Server}};'
            'SERVER={scheme}:{hostname},{port};'
            'DATABASE={database};'
            'UID={username};'
            'PWD={password}'
            .format(**uri_parsed)
        )

        self._cursor = self._sql_server_client.cursor()
        self._table_name = collection
        self._primary_key = primary_key

        self._select_all_query = "SELECT * from {table};".format(table=self._table_name)
        self._insert_query = "INSERT into {table}({{attributes}}) VALUES ({{values}});".format(table=self._table_name)
        self._select_query = "SELECT * from {table} where {primary_key}='{{value}}'".format(
            table=self._table_name, primary_key=self._primary_key)
        self._del_query = "DELETE from {table} where {primary_key} = {{value}};".format(table=self._table_name,
                                                                                        primary_key=self._primary_key)

    @classmethod
    def from_kwargs(cls, database, username, password, host='localhost', port=1433, conn_protocol='tcp', **kwargs):
        uri = build_uri(conn_protocol, database, username, password, host, port)
        return cls(uri, **kwargs)

    @staticmethod
    def __check_dependencies():
        if 'ubuntu' in platform.platform().lower():
            result = subprocess.Popen(["dpkg", "-s", "msodbcsql17"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = result.communicate()
            if not out:
                raise ModuleNotFoundError("ODBC Driver for SQL Server is missing. Please refer "
                                          "https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-"
                                          "microsoft-odbc-driver-for-sql-server?view=sql-server-2017")

    def __getitem__(self, k):
        self._cursor.execute(self._select_query.format(value=k))
        record = self._cursor.fetchone()
        return record if record else print(f"No record found for primary_key: {k}")
        # TODO: Raise a proper exception here

    def __setitem__(self, k, v):
        _sanitized_values = [str(val) if isinstance(val, int) else "'{}'".format(val) for val in v.values()]
        try:
            self._cursor.execute(self._insert_query.format(attributes=','.join(v.keys()),
                                                           values=','.join(_sanitized_values)))
        except pyodbc.IntegrityError as e:
            # TODO: Raise a proper exception here
            print("ERROR: Cannot insert a duplicate entry")

        self._sql_server_client.commit()

    def __delitem__(self, k):
        self._cursor.execute(self._del_query.format(value=k))
        self._sql_server_client.commit()

    def __iter__(self):
        self._cursor.execute(self._select_all_query)
        records = self._cursor.fetchall()

        for record in records:
            yield record

    def __len__(self):
        self._cursor.execute(self._select_all_query)
        records = self._cursor.fetchall()
        return len(records)


def test_sqlserver_persister():
    sql_server_persister = SQLServerPersister()

    print("Fetching a Record")
    print(sql_server_persister[1])
    print(sql_server_persister[3])
    print("=========================")

    print("Adding a Record")
    sql_server_persister[3] = {'id': "3",
                               'name': 'new name'}
    sql_server_persister[4] = {'id': "4",
                               'name': 'Hamid NEW'}
    sql_server_persister[5] = {'id': "5",
                               'name': 'Hamid NEW AGAIN'}

    print(sql_server_persister[3])
    print(sql_server_persister[4])
    print(sql_server_persister[5])
    print("======================")

    print("Deleting a Record")
    del sql_server_persister[3]
    del sql_server_persister[4]
    del sql_server_persister[5]
    print(sql_server_persister[3])
    print("=====================")

    print("Iterating over the records")
    for record in sql_server_persister:
        print(record)
    print("=========================")

    print("Getting the length")
    print(len(sql_server_persister))
