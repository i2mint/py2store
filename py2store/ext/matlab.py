"""
a data object layer for matlab
"""
from io import BytesIO
from contextlib import suppress

with suppress(ModuleNotFoundError, ImportError):
    from py2store.ext.hdf import HdfFileReader, HdfDatasetReader, HdfRefReader

    def read_matlab_bytes_with_scipy(b: bytes):
        """Note: Doesn't work after matlab 7.3. For >= 7.3, use hdf."""
        from scipy.io import loadmat

        return loadmat(BytesIO(b))

    def read_matlab_bytes_with_h5py(b: bytes):
        import h5py

        return h5py.File(BytesIO(b), 'r')
