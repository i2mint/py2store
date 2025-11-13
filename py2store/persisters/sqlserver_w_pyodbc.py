import platform
import subprocess
from collections.abc import MutableMapping
from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    import pyodbc


class SQLServerPersister(MutableMapping):
    def __init__(self,
                 conn_protocol='tcp',
                 host='localhost',
                 port='1433',
                 db_username='SA',
                 db_pass='Admin123x',
                 db_name='py2store',
                 table_name='py2store_default_table',
                 key_fields=('id',),
                 data_fields=('name',),
                 create_table_if_not_exists=True,
                 NVARCHAR_LENGTH=100):
        """

        :param conn_protocol: Which connection protocol to use to connect to MS SQLServer
        :param host: HOST where SQLServer is running
        :param port: PORT of SQLServer
        :param db_username: Username tht will be used to connect to the SQLServer
        :param db_pass: Database password
        :param db_name: Database Name, to connect to
        :param table_name: Table name on which you are going to perform CRUD ops
        :param key_fields: Primary key fields of the table
        :param data_fields: Non primary fields of the table
        :param create_table_if_not_exists: Flag to create database table if it doesn't exist previously
        :param NVARCHAR_LENGTH: Length of the NVARCHAR column types in case the table isn't created previously
        """

        self.__check_dependencies()
        self._sql_server_client = pyodbc.connect('DRIVER={{ODBC Driver 17 for SQL Server}};'
                                                 'SERVER={}:{},{};'
                                                 'DATABASE={};'
                                                 'UID={};'
                                                 'PWD={}'
                                                 .format(conn_protocol, host, port, db_name, db_username, db_pass))

        self._cursor = self._sql_server_client.cursor()

        self._table_name = table_name
        self.key_fields = key_fields
        self.data_fields = data_fields
        self.NVARCHAR_LENGTH = NVARCHAR_LENGTH

        if create_table_if_not_exists:
            self.__create_table()

    def __create_table(self):
        """
        Create table if it doesn't exist previously
        :return:
        """
        if not self._cursor.tables(table=self._table_name, tableType='TABLE').fetchone():
            base_query = 'CREATE TABLE {table_name} ({attributes})'
            attributes = ''

            for key_field in self.key_fields:
                attributes += '{column} {type} PRIMARY KEY,'.format(column=key_field,
                                                                    type='NVARCHAR({})'.format(self.NVARCHAR_LENGTH))

            for data_field in self.data_fields:
                attributes += '{column} {type},'.format(column=data_field, type='NVARCHAR(100)')

            create_table_query = base_query.format(table_name=self._table_name, attributes=attributes)

            self._cursor.execute(create_table_query)
            self._sql_server_client.commit()

    @staticmethod
    def __check_dependencies():
        """
        Checks for the required dependencies for the OS
        Currently checks are there for a Ubuntu machine only, more can be added
        :return:
        """
        if 'ubuntu' in platform.platform().lower():
            result = subprocess.Popen(["dpkg", "-s", "msodbcsql17"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = result.communicate()
            if not out:
                raise ModuleNotFoundError("ODBC Driver for SQL Server is missing. Please refer "
                                          "https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-"
                                          "microsoft-odbc-driver-for-sql-server?view=sql-server-2017")

    def __getitem__(self, k):
        base_query = "SELECT * from {table} where {{conditions}}".format(table=self._table_name)

        conditions = ''
        for key, val in k.items():
            conditions += "{key} = '{val}' AND ".format(key=key, val=val)

        select_query = base_query.format(conditions=conditions)
        select_query = select_query.rstrip('AND ')

        self._cursor.execute(select_query.format(value=k))
        record = self._cursor.fetchone()
        if record:
            return record
        raise KeyError(f"No record found for primary_key: {k}")

    def __setitem__(self, k, v):
        base_query = "INSERT into {table} ({{attributes}}) VALUES ({{values}})".format(table=self._table_name)

        attributes = ','.join([key for key in k])
        values = ','.join(["'{}'".format(val) for val in v])
        insert_query = base_query.format(attributes=attributes, values=values)

        try:
            self._cursor.execute(insert_query)
        except pyodbc.IntegrityError as e:
            raise KeyError("Cannot insert a duplicate entry")

        self._sql_server_client.commit()

    def __delitem__(self, k):
        base_query = "DELETE FROM {table} where {{conditions}}".format(table=self._table_name)

        conditions = ''
        for key, val in k.items():
            conditions += "{key} = '{val}' AND ".format(key=key, val=val)

        select_query = base_query.format(conditions=conditions)
        select_query = select_query.rstrip('AND ')

        self._cursor.execute(select_query.format(value=k))
        self._sql_server_client.commit()

    def __iter__(self):
        select_all_query = "SELECT * from {table};".format(table=self._table_name)
        self._cursor.execute(select_all_query)
        records = self._cursor.fetchall()

        for record in records:
            yield record

    def __len__(self):
        select_all_query = "SELECT * from {table};".format(table=self._table_name)
        self._cursor.execute(select_all_query)
        records = self._cursor.fetchall()
        return len(records)


def test_sqlserver_persister():
    """
    A test case for the persister which performs many actions

    Output of the test case is given below:

                Adding Records
                =========================
                Adding a Duplicate Record
                Cannot Enter a Duplicate Record
                =========================
                Fetching Records
                ('1', 'Test 1')
                ('2', 'Test 2')
                ('3', 'Test 3')
                =========================
                Iterating over the records
                ('1', 'Test 1')
                ('2', 'Test 2')
                ('3', 'Test 3')
                =========================
                Getting the length
                3
                =====================
                Deleting Records
                =====================
                Getting the length AGAIN after deletion
                0
                =====================

    :return:
    """
    sql_server_persister = SQLServerPersister()

    print("Adding Records")
    sql_server_persister[('id', 'name',)] = ('1', 'Test 1',)
    sql_server_persister[('id', 'name',)] = ('2', 'Test 2',)
    sql_server_persister[('id', 'name',)] = ('3', 'Test 3',)
    print("=========================")

    print("Adding a Duplicate Record")
    try:
        sql_server_persister[('id', 'name',)] = ('1', 'Test 4',)
    except KeyError:
        print("Cannot Enter a Duplicate Record")
    print("=========================")

    print("Fetching Records")
    print(sql_server_persister[{'id': '1',
                                'name': 'Test 1'}])
    print(sql_server_persister[{'name': 'Test 2'}])
    print(sql_server_persister[{'id': 3}])
    print("=========================")

    print("Iterating over the records")
    for record in sql_server_persister:
        print(record)
    print("=========================")

    print("Getting the length")
    print(len(sql_server_persister))
    print("=====================")

    print("Deleting Records")
    del sql_server_persister[{'id': '1'}]
    del sql_server_persister[{'name': 'Test 2'}]
    del sql_server_persister[{'id': '3', 'name': 'Test 3'}]
    print("=====================")

    print("Getting the length AGAIN after deletion")
    print(len(sql_server_persister))
    print("=====================")


test_sqlserver_persister()
