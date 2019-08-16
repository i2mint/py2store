import boto3

from py2store.base import Persister


class NoSuchKeyError(KeyError):
    pass


class DynamoDbPersister(Persister):
    '''
    A basic DynamoDb via Boto3 persister.
    >>> from py2store.persisters.dynamodb_w_boto3 import DynamoDbPersister
    >>> s = DynamoDbPersister()
    >>> k = {'key': '777'} # Each collection will happily accept user-defined _key values.
    >>> v = {'val': 'bar'}
    >>> for _key in s:
    ...     del s[_key]
    ...
    >>> k in s
    False
    >>> len(s)
    0
    >>> s[k] = v
    >>> len(s)
    1
    >>> s[k]
    {'val': 'bar'}
    >>> s.get(k)
    {'val': 'bar'}
    >>> s.get({'not': 'a key'}, {'default': 'val'})  # testing s.get with default
    {'default': 'val'}
    >>> list(s.values())
    [{'val': 'bar'}]
    >>> k in s  # testing __contains__ again
    True
    >>> del s[k]
    >>> len(s)
    0
    >>> s = DynamoDbPersister(table_name='py2store2', key_fields=('name',))
    >>> for _key in s:
    ...   del s[_key]
    >>> len(s)
    0
    >>> s[{'name': 'guido'}] = {'yob': 1956, 'proj': 'python', 'bdfl': False}
    >>> s[{'name': 'guido'}]
    {'proj': 'python', 'yob': Decimal('1956'), 'bdfl': False}
    >>> s[{'name': 'vitalik'}] = {'yob': 1994, 'proj': 'ethereum', 'bdfl': True}
    >>> s[{'name': 'vitalik'}]
    {'proj': 'ethereum', 'yob': Decimal('1994'), 'bdfl': True}
    >>> for key, val in s.items():
    ...   print(f"{key}: {val}")
    {'name': 'vitalik'}: {'proj': 'ethereum', 'yob': Decimal('1994'), 'bdfl': True}
    {'name': 'guido'}: {'proj': 'python', 'yob': Decimal('1956'), 'bdfl': False}
    '''
    def __init__(
            self,
            aws_access_key_id='',
            aws_secret_access_key='',
            region_name='us-west-2',
            endpoint_url="http://localhost:8000",
            table_name='py2store',
            key_fields=('key',),
            data_fields=('data',)
    ):
        self._dynamodb = boto3.resource('dynamodb', region_name=region_name, endpoint_url=endpoint_url,
                                  aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        if isinstance(key_fields, str):
            key_fields = (key_fields,)

        self._key_fields = key_fields

        if isinstance(data_fields, str):
            data_fields = (data_fields,)

        self._data_fields = data_fields

        key_schema = [{'AttributeName': k, 'KeyType': 'HASH'} for k in self._key_fields]
        attribute_definition = [{'AttributeName': k, 'AttributeType': 'S'} for k in self._key_fields]

        try:
            self._table = self._dynamodb.create_table(TableName=table_name,
                                                      KeySchema=key_schema,
                                                      AttributeDefinitions=attribute_definition,
                                                      ProvisionedThroughput={
                                                            'ReadCapacityUnits': 5,
                                                            'WriteCapacityUnits': 5,
                                                        }
                                                      )
            # Wait until the table creation complete.
            self._table.meta.client.get_waiter('table_exists').wait(TableName='Employee')
            print('Table has been created, please continue to insert data.')
        except Exception:
            self._table = self._dynamodb.Table(table_name)
            pass

    def __getitem__(self, k):
        try:
            if isinstance(k, str):
                k = (k,)
                k = {att: key for att, key in zip(self._key_fields, k)}
            response = self._table.get_item(Key=k)
            d = response['Item']
            return {x: d[x] for x in d if x not in self._key_fields}
        except Exception as e:
            raise NoSuchKeyError("Key wasn't found: {}".format(k))

    def __setitem__(self, k, v):
        if isinstance(k, str):
            k = (k,)
            key = {att: key for att, key in zip(self._key_fields, k)}
        else:
            key = k
        if isinstance(v, str):
            v = (v,)
            val = {att: key for att, key in zip(self._data_fields, v)}
        else:
            val = v

        self._table.put_item(Item={**key, **val})

    def __delitem__(self, k):
        try:
            if isinstance(k, str):
                k = (k,)
                key = {att: key for att, key in zip(self._key_fields, k)}
            else:
                key = k
            self._table.delete_item(Key=key)
        except Exception as e:
            if hasattr(e, '__name__'):
                if e.__name__ == 'NoSuchKey':
                    raise NoSuchKeyError("Key wasn't found: {}".format(k))
            raise  # if you got so far

    def __iter__(self):
        response = self._table.scan()
        yield from [{x: d[x] for x in d if x in self._key_fields} for d in response['Items']]

    def __len__(self):
        response = self._table.scan()
        return len(response['Items'])
