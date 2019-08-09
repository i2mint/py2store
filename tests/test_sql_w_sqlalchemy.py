import logging

from py2store.persisters.sql_w_sqlalchemy import SQLAlchemyPersister


logger = logging.getLogger(__name__)
logging.basicConfig(level='INFO')


def test_sqlalchemy_persister():
    key = {
        'first_name': 'Yuri',
        'last_name': 'Gagarin',
    }
    data = {
        'height': '185sm',
        'weight': '80kg',
        'is_hero': 'yes he is',
    }
    joined_values = {**key, **data}

    sql_dict = SQLAlchemyPersister(
        collection_name='tmp',
        key_fields=list(key.keys()),
        data_fields=list(data.keys()),
    )

    logger.info('Deleting all docs in DB...')
    for _id in sql_dict:  # deleting all docs in tmp
        del sql_dict[_id]

    logger.info('See that key is not in store (and testing __contains__)...')
    assert key not in sql_dict
    assert len(sql_dict) == 0

    logger.info('Assigning a value to a new key...')
    sql_dict[key] = data
    assert len(sql_dict) == 1

    for k, v in joined_values.items():
        object_from_db = sql_dict[key]
        assert getattr(object_from_db, k) == v

    assert sql_dict.get(key) == object_from_db

    logger.info('Testing s.get with default...')
    assert sql_dict.get({'first_name': 'totally not Yuri'}, 'default val') == 'default val'

    logger.info('Testing __contains__ again...')
    assert key in sql_dict

    logger.info('Testing deleting key...')
    del sql_dict[key]
    assert len(sql_dict) == 0

    logger.info('Success!')
