from collections import Sized, Iterable
from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from sqlalchemy import create_engine, Column, String, Table
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    import sqlalchemy as db

from py2store.base import Persister

from py2store.base import Collection, KvReader

DFLT_SQL_PORT = 1433
DFLT_SQL_HOST = 'localhost'


class SqlTable(Sized, Iterable):
    """Object wrapping a table. It is Iterable (yields rows (as tuples)) and Sized (i.e. you can call len on it)"""
    _tmpl_count_rows_tmpl = 'SELECT COUNT(*) FROM {table_name}'
    _tmpl_describe_tmpl = 'DESCRIBE {table_name}'
    _tmpl_iter_tmpl = 'SELECT * FROM {table_name}'

    def __init__(self, connection, table_name):
        self.connection = connection
        self.table_name = table_name

    # Helpers ##########################################################################################################
    # QUESTION: Should helpers (_describe, _columns, etc.) should be methods/properties/lazyprops, and hidden or not?

    def _count_rows(self):
        return self.connection.execute(self._tmpl_count_rows_tmpl.format(table_name=self.table_name))

    def _describe(self):
        return self.connection.execute(self._tmpl_describe_tmpl.format(table_name=self.table_name))

    @property
    def _columns(self):
        return tuple(x[0] for x in self._describe())

    ####################################################################################################################

    def __iter__(self):
        yield from self.connection.execute(self._tmpl_iter_tmpl.format(table_name=self.table_name))

    def __len__(self):
        return self._count_rows().first()[0]

    def __repr__(self):
        return f"SqlTable(..., table_name={self.table_name}"


class SqlDatabaseCollection(Collection):
    """A collection of sql tables names."""

    def __init__(self, connection):
        self.connection = connection

    @classmethod
    def from_connection(cls, connection):
        pass  # TODO: Need to make object (with __new__) manually to do this?

    @classmethod
    def from_engine(cls, engine):
        connection = engine.connect()
        o = cls(connection)
        o.engine = engine
        return o

    @classmethod
    def from_uri(cls, uri):
        engine = db.create_engine(uri)
        o = cls.from_engine(engine)
        o.uri = uri
        return o

    @classmethod
    def from_config_dict(cls, config_dict):
        # handle defaults
        config_dict = dict(dict(host=DFLT_SQL_HOST, port=DFLT_SQL_PORT), **config_dict)

        # validate input
        expected_keys = {'user', 'pwd', 'host', 'port', 'database'}
        assert {key for key in config_dict.keys() if key in expected_keys} == expected_keys, 'incomplete config'

        # make the uri
        uri = 'mysql+pymysql://{user}:{pwd}@{host}:{port}/{database}'.format(**config_dict)  # connect to database

        # make an instance from uri
        o = cls.from_uri(uri)
        o.config_dict = config_dict
        return o

    @classmethod
    def from_configs(cls, database, user='user', pwd='password', port=DFLT_SQL_PORT, host=DFLT_SQL_HOST):
        return cls.from_config_dict(dict(database=database, user=user, pwd=pwd, port=port, host=host))

    def __iter__(self):
        yield from (x[0] for x in self.connection.execute('show tables'))


class SqlReader(SqlDatabaseCollection, KvReader):
    """A KvReader of sql tables. Keys are table names and values are SqlTable objects"""

    def __getitem__(self, k):
        return SqlTable(self.connection, k)


# More explicit aliases
SqlAlchemyReader = SqlReader
SqlAlchemyDatabaseCollection = SqlDatabaseCollection


class DfSqlReader(SqlReader):
    def __getitem__(self, k):
        with ModuleNotFoundErrorNiceMessage():
            import pandas as pd
        table = super().__getitem__(k)
        return pd.DataFrame(data=list(table), columns=table._columns)


class SQLAlchemyPersister(Persister):
    """
    A basic SQL DB persister written with SQLAlchemy.
    """

    def __init__(
            self,
            db_uri='sqlite:///my_sqlite.db',
            collection_name='py2store_default_table',
            key_fields=('id',),
            data_fields=('data',),
            autocommit=True,
            **db_kwargs
    ):
        """
        :param db_uri: Uniform Resource Identifier of a database you would like to use.
            Unix/Mac (note the four leading slashes)
                sqlite:////absolute/path/to/foo.db

            Windows (note 3 leading forward slashes and backslash escapes)
                sqlite:///C:\\absolute\\path\\to\\foo.db

            Or go for in-memory DB with NO PERSISTANCE:
            sqlite:///:memory:

            Other options:
                postgresql://user:password@localhost:5432/my_db
                mysql://user:password@localhost/db
                oracle://user:password:tiger@localhost:1521/sidname

            I.e. in general:
                dialect+driver://username:password@host:port/database

        :param collection_name: name of the table to use, i.e. "my_table".
        :param key_fields: indexed keys columns names.
        :param data_fields: non-indexed data columns names.
        :param autocommit: whether each data change should be instantly commited, or not.
            It's off for context manager usecase (tbd).

        :param kwargs: any extra kwargs for SQLAlchemy engine to setup.
        """
        self._key_fields = key_fields
        self._data_fields = data_fields
        self.autocommit = autocommit

        self.connection = None
        self.table = None
        self.session = None

        self.setup(db_uri, collection_name, **db_kwargs)

    def setup(self, db_uri, collection_name, **db_kwargs):
        # Setup connection to our DB:
        engine = create_engine(db_uri, **db_kwargs)
        self.connection = engine.connect()

        # Create a table:
        self.table = self._create_table(collection_name, engine)

        # Open ORM session:
        self.session = sessionmaker(bind=engine)()

    def teardown(self):
        self.session.close()
        self.connection.close()

    def _create_table(self, table_name, engine):
        """ Create our data table (if not there yet). """
        Base = declarative_base()

        table = Table(
            table_name,
            Base.metadata,
            *[
                Column(key, String(), primary_key=True, index=True)
                for key in self._key_fields
            ],
            *[
                Column(name, String())
                for name in self._data_fields
            ],
        )
        table.create(bind=engine, checkfirst=True)

        # Lets wrap our Table with Base so we'll be able to use ORM features later.
        class DeclarativeTable(Base):
            __table__ = table

        return DeclarativeTable

    @property
    def query(self):
        return self.session.query(self.table)

    def __getitem__(self, k):
        doc = self.query.filter_by(**k).first()
        # todo: think of intuitive way of selecting many by 1 (or some) of many keys
        if not doc:
            raise KeyError(f"No document found for query: {k}")

        return doc

    def __setitem__(self, k, v):
        try:
            doc = self[k]
        except KeyError:
            doc = self.table(**k, **v)
            self.session.add(doc)
        else:
            for key, value in v.items():
                setattr(doc, key, value)

        if self.autocommit:
            self.session.commit()

    def __delitem__(self, k):
        doc = self[k]
        self.session.delete(doc)

        if self.autocommit:
            self.session.commit()

    def __iter__(self):
        yield from self.query

    def __len__(self):
        return self.query.count()

    def __del__(self):
        self.teardown()
