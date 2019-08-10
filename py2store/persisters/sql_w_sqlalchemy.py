import logging

try:
    from sqlalchemy import create_engine, Column, String
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
except ImportError as e:
    raise ImportError(f"""
    It seems you don't have sqlalchemy, or some extension of it.
    Try installing it by running
        pip install SQLAlchemy
    in your terminal.
    For more information: https://pypi.org/project/SQLAlchemy/
    -------- Original error message --------
    {e}
    """)

from py2store.base import Persister


class BaseDataTable:
    id = Column(String, primary_key=True, index=True)
    data = Column(String)

    def __repr__(self):
        return str((self.id, self.data))


class SQLAlchemyPersister(Persister):
    """
    A basic SQL DB persister written with SQLAlchemy.
    """

    def __init__(
            self,
            db_uri='sqlite:///my_sqlite.db',
            collection_name='py2store_default_table',
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
        :param kwargs: any extra kwargs for SQLAlchemy engine to setup.
        """
        self.db = self.setup_connection(db_uri, db_kwargs)
        self.table = self.create_table(collection_name)

        # Open ORM session:
        self.session = sessionmaker(bind=self.db)()

    def setup_connection(self, db_uri, db_kwargs):
        """ Setup connection to our DB and check it. """
        db = create_engine(db_uri, **db_kwargs)
        db.connect()
        return db

    def create_table(self, table_name):
        """ Create our data table (if not there yet). """
        Base = declarative_base()

        class DataTable(BaseDataTable, Base):
            __tablename__ = table_name

        Base.metadata.create_all(self.db, checkfirst=True)
        return DataTable

    def __getitem__(self, k):
        doc = self.session.query(self.table).get(k)
        if doc is not None:
            return doc.data
        else:
            raise KeyError(f"No document found for query: {k}")

    def __setitem__(self, k, v):
        doc = self.table(id=k, data=v)
        self.session.add(doc)
        self.session.commit()  # todo: needs optimization.

    def __delitem__(self, k):
        doc = self.session.query(self.table).get(k)
        if not doc:
            raise KeyError(f"You can't removed that key: {k}")

        self.session.delete(doc)
        self.session.commit()

    def __iter__(self):
        keys_gen = (
            i[0] for i in
            self.session.query(self.table)
                .values(self.table.id)
        )
        yield from keys_gen

    def __len__(self):
        return self.session.query(self.table).count()


def test_sqlalchemy_persister():
    logger = logging.getLogger(__name__)
    logging.basicConfig(level='INFO')

    key = 'foo'
    value = 'bar'

    sql_dict = SQLAlchemyPersister(collection_name='tmp')

    logger.info('Deleting all docs in DB...')
    for _id in sql_dict:  # deleting all docs in tmp
        del sql_dict[_id]

    logger.info('See that key is not in store (and testing __contains__)...')
    assert key not in sql_dict
    assert len(sql_dict) == 0

    logger.info('Assigning a value to a new key...')
    sql_dict[key] = value
    assert len(sql_dict) == 1
    assert list(sql_dict) == [key]
    assert sql_dict[key] == value
    assert sql_dict.get(key) == value

    logger.info('Testing s.get with default...')
    assert sql_dict.get('not a key', 'default val') == 'default val'
    assert list(sql_dict.values()) == [value]

    logger.info('Testing __contains__ again...')
    assert key in sql_dict

    logger.info('Testing deleting key...')
    del sql_dict[key]
    assert len(sql_dict) == 0

    logger.info('Success!')
