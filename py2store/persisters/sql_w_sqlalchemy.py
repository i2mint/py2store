from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    from sqlalchemy import create_engine, Column, String, Table
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

from py2store.base import Persister


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
