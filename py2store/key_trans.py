class ExpliticKeyTrans:
    """
    >>> from py2store.trans import kv_wrap
    >>> d = {'one': 'stone', 'two': 'get', 'three': 'birds'}
    >>> dd =
    """

    def __init__(self, id_of_key=None, key_of_id=None):
        if id_of_key is None:
            if key_of_id is None:
                raise ValueError("You need to specify at least one of these: id_of_key, or key_of_id (or both!)")
            else:
                id_of_key = {k: _id for _id, k in key_of_id.items()}
        elif key_of_id is None:
            key_of_id = {_id: k for k, _id in id_of_key.items()}
        self.id_of_key = id_of_key
        self.key_of_id = key_of_id

    def _key_of_id(self, _id):
        return self.key_of_id[_id]

    def _id_of_key(self, k):
        return self.id_of_key[k]

    # TODO: These two functions are general and should be placed in another Mixin or function
    def _test_key_id_key_invertability(self, k):
        return k == self._key_of_id(self._id_of_key(k))

    def _test_id_key_id_invertability(self, _id):
        return _id == self._id_of_key(self._key_of_id(_id))
