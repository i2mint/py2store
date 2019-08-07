import platform
import subprocess
from collections.abc import MutableMapping


class SQLServerPersister(MutableMapping):
    def __init__(self, conn_protocol='tcp', host='localhost', port='1433', db_username='SA', db_pass='Admin123x',
                 db_name='py2store', table_name='person', primary_key='id', data_fields=('name',)):

        self.__check_dependencies()
        self._sql_server_client = pyodbc.connect('DRIVER={{ODBC Driver 17 for SQL Server}};'
                                                 'SERVER={}:{},{};'
                                                 'DATABASE={};'
                                                 'UID={};'
                                                 'PWD={}'
                                                 .format(conn_protocol, host, port, db_name, db_username, db_pass))

        self._cursor = self._sql_server_client.cursor()
        self._table_name = table_name
        self._primary_key = primary_key

        self._select_all_query = "SELECT * from {table};".format(table=self._table_name)
        self._insert_query = "INSERT into {table}({{attributes}}) VALUES ({{values}});".format(table=self._table_name)
        self._select_query = "SELECT * from {table} where {primary_key}='{{value}}'".format(
            table=self._table_name, primary_key=self._primary_key)
        self._del_query = "DELETE from {table} where {primary_key} = {{value}};".format(table=self._table_name,
                                                                                        primary_key=self._primary_key)

    @staticmethod
    def __check_dependencies():
        import pkg_resources
        installed_packages = [pkg.project_name for pkg in pkg_resources.working_set]
        if 'pyodbc' not in installed_packages:
            raise ModuleNotFoundError("'SQLServerPersister' depends on the module 'pyodbc' which is not installed. "
                                      "Try installing dependency using 'pip install pyodbc'.")

        # import pyodbc globally
        global pyodbc
        import pyodbc

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


test_sqlserver_persister()
