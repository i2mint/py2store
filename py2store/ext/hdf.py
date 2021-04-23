"""
a data object layer for HDF files
"""
from io import BytesIO
from dol import KvReader

from contextlib import suppress

with suppress(ModuleNotFoundError):
    from h5py import File
    from h5py.h5r import get_name
    import numpy as np

    class HdfFileReader(KvReader):
        def __init__(self, src):
            if isinstance(src, bytes):
                src = BytesIO(src)
            self._src = File(src, 'r')

        def __iter__(self):
            return self._src.__iter__()

        def __getitem__(self, k):
            return HdfDatasetReader(self._src.__getitem__(k), self._src)

    class HdfDatasetReader(KvReader):
        def __init__(self, src, root=None):
            self._src = src
            self._root = root

        def __iter__(self):
            return self._src.__iter__()

        def __getitem__(self, k):
            return HdfRefReader(self._src.__getitem__(k), self._root)

    class HdfRefReader(KvReader):
        def __init__(self, src, root):
            self._src = src
            self._root = root

        def __iter__(self):
            return (get_name(ref, self._root.id) for ref in self._src)

        def __getitem__(self, k):
            return np.array(self._root[k])
