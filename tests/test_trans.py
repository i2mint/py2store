import pytest
from py2store.trans import wrap_kvs


def test_wrap_kvs():
    def test_a_class(A, offset=100):
        a = A()

        ######### Test that id_of_key works (all outgoing keys are lower cased) #########
        val = 1
        a['KEY'] = val
        # repr is just the base class (dict) repr, so shows "inside" the store (lower case keys and +100)
        assert str(a) == f"{{'key': {val + offset}}}"

        val = 2
        a['key'] = val
        # repr is just the base class (dict) repr, so shows "inside" the store (lower case keys and +100)
        assert str(a) == f"{{'key': {val + offset}}}"

        val = 3
        a['kEy'] = val
        # repr is just the base class (dict) repr, so shows "inside" the store (lower case keys and +100)
        assert str(a) == f"{{'key': {val + offset}}}"

        ######### from the point of view of the interface the keys are all upper case #########
        assert list(a) == ['KEY']

        assert list(a.items()) == [('KEY', val)]  # and the values are those we put there.

    def key_of_id(_id):
        return _id.upper()

    def id_of_key(k):
        return k.lower()

    def obj_of_data(data):
        return data - 100

    def data_of_obj(obj):
        return obj + 100

    A = wrap_kvs(dict, 'A',
                 key_of_id=key_of_id, id_of_key=id_of_key, obj_of_data=obj_of_data, data_of_obj=data_of_obj)

    test_a_class(A)

    class T:
        offset = 100

        def key_of_id(_id):
            return _id.upper()

        def id_of_key(k):
            return k.lower()

        def obj_of_data(data):
            return data - T.offset

        def data_of_obj(obj):
            return obj + T.offset

    A = wrap_kvs(dict, 'A',
                 key_of_id=T.key_of_id, id_of_key=T.id_of_key,
                 obj_of_data=T.obj_of_data, data_of_obj=T.data_of_obj)

    test_a_class(A)

    class T:
        def __init__(self, offset):
            self.offset = 100

        @staticmethod
        def key_of_id(_id):
            return _id.upper()

        @staticmethod
        def id_of_key(self, k):  # decoy! It's a static method, but first argument is called "self"
            return k.lower()

        def obj_of_data(self, data):
            return data - self.offset

        def data_of_obj(self, obj):
            return obj + self.offset

    t = T(100)
    A = wrap_kvs(dict, 'A',
                 key_of_id=t.key_of_id, id_of_key=t.id_of_key,
                 obj_of_data=t.obj_of_data, data_of_obj=t.data_of_obj)

    test_a_class(A)

    t = T(50)
    A = wrap_kvs(dict, 'A',
                 key_of_id=t.key_of_id, id_of_key=t.id_of_key,
                 obj_of_data=t.obj_of_data, data_of_obj=t.data_of_obj)

    test_a_class(A)

    ###################### Test postget ####################
    B = wrap_kvs(dict, 'B', postget=lambda k, v: f'upper {v}' if k[0].isupper() else f'lower {v}')

    b = B()

    b['BIG'] = 'letters'

    b['small'] = 'text'

    assert list(b.items()) == [('BIG', 'upper letters'), ('small', 'lower text')]

    to_csv = lambda LoL: '\\n'.join(map(','.join, map(lambda L: (x for x in L), LoL)))

    from_csv = lambda csv: list(map(lambda x: x.split(','), csv.split('\\n')))

    LoL = [['a', 'b', 'c'], ['d', 'e', 'f']]

    assert from_csv(to_csv(LoL)) == LoL

    ###################### Test preset and postget ####################

    import json, pickle

    def preset(k, v):
        if k.endswith('.csv'):
            return to_csv(v)
        elif k.endswith('.json'):
            return json.dumps(v)
        elif k.endswith('.pkl'):
            return pickle.dumps(v)
        else:
            return v  # as is

    def postget(k, v):
        if k.endswith('.csv'):
            return from_csv(v)
        elif k.endswith('.json'):
            return json.loads(v)
        elif k.endswith('.pkl'):
            return pickle.loads(v)
        else:
            return v  # as is

    mydict = wrap_kvs(dict, preset=preset, postget=postget)

    obj = [['a', 'b', 'c'], ['d', 'e', 'f']]

    d = mydict()

    d['foo.csv'] = obj  # store the object as csv

    # the str of a dict by-passes the transformations, so we see the data in the "raw" format it is stored in.
    assert str(d) == str({'foo.csv': 'a,b,c\\nd,e,f'})
    # but if we actually ask for the data, it deserializes to our original object
    assert d['foo.csv'] == [['a', 'b', 'c'], ['d', 'e', 'f']]

    d['bar.json'] = obj  # store the object as json
    assert str(d) == str({'foo.csv': 'a,b,c\\nd,e,f', 'bar.json': '[["a", "b", "c"], ["d", "e", "f"]]'})

    assert d['bar.json'] == [['a', 'b', 'c'], ['d', 'e', 'f']]

    d['bar.json'] = {'a': 1, 'b': [1, 2], 'c': 'normal json'}  # let's write a normal json instead.
    assert str(d) == str({'foo.csv': 'a,b,c\\nd,e,f', 'bar.json': '{"a": 1, "b": [1, 2], "c": "normal json"}'})

    assert len(d) == 2
    del d['foo.csv']
    assert len(d) == 1
    del d['bar.json']
    assert len(d) == 0

    d['foo.pkl'] = obj  # 'save' obj as pickle
    assert d['foo.pkl'] == obj


if __name__ == '__main__':
    pytest.main()
