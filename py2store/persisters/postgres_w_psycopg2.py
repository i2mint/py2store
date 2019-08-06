from py2store.base import Persister
import psycopg2

raise NotImplementedError("Unfinished module.")


class DBPersister(Persister):
    def __init__(self, db_name, user, password, **kwargs):
        port = kwargs.get('port', "5432")
        host = kwargs.get('host', "127.0.0.1")
        self.table = kwargs.get('table', 'py2store')
        self.connection = psycopg2.connect(
            user=user,
            database=db_name,
            password=password,
            port=port,
            host=host)
        self.cursor = self.connection.cursor()

    def __getitem__(self, key):
        sql = f'''select data from {self.table} where skye="{key}"'''
        self.cursor.execute(sql)
        row = self.cursor.fetchone()
        return row[0]

    def __setitem__(self, key, value):
        sql = f'''update {self.table} set data="{value}"'''
        self.cursor.execute(sql)
        self.connection.commit()

    def __delitem__(self, key):
        sql = f'''delete from {self.table} where skye="{key}"'''
        self.cursor.execute(sql)
        self.connection.commit()
