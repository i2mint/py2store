import os
from ppy.deco import lazyprop
from ocore.utils.nothing import nothing


# TODO: (1) This is an example using csv files for content. Generalize append functionality to handle any backend
# TODO: (2) The class should transparently offer access to _contents, forwarding all attrs to it

class AppendToFile:
    def __init__(self, filepath):
        self.filepath = filepath

    @lazyprop
    def _contents(self):
        if not os.path.isfile(self.filepath):
            self._mk_empty_file()
            return nothing
        else:
            with open(self.filepath, 'r') as fp:
                return list(map(self._data_to_val, fp.read().splitlines()))

    def _mk_empty_file(self):
        with open(self.filepath, 'w') as fp:
            fp.write('')

    def _val_to_data(self, v):
        if not hasattr(v, '__iter__'):
            v = (v,)
        return ','.join(map(str, v))

    def _data_to_val(self, data):
        return tuple(data.split(','))

    #         v = list()
    #         for row in data.split('\n'):
    #             v.append(row.split(','))
    #         return v

    def __iadd__(self, v):
        self._contents += [v]
        with open(self.filepath, 'a+') as fp:
            fp.write(self._val_to_data(v) + '\n')

    def clear(self):
        if hasattr(self, '_contents'):
            del self._contents
        os.remove(self.filepath)


def test_simple():
    a = AppendToFile('test.csv')
    a.clear()
    assert a._contents == nothing

    a.__iadd__((3, 'foo'))
    assert a._contents == [(3, 'foo')]

    a.__iadd__((10, 'bar'))
    assert a._contents == [(3, 'foo'), (10, 'bar')]

    # what if another object is created with that same file?
    aa = AppendToFile('test.csv')
    assert aa._contents == [('3', 'foo'), ('10', 'bar')]
    # NOTE that you don't have numbers any more, but only strings

    a.clear()  # namely, to get rid of that test file


if __name__ == '__main__':
    test_simple()

    # import pytest
    # pytest.main()
