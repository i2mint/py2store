"""
a data object layer for matlab
"""
from io import BytesIO
from contextlib import suppress

with suppress(ModuleNotFoundError, ImportError):
    from py2store.ext.hdf import HdfFileReader, HdfDatasetReader, HdfRefReader

    def read_matlab_bytes_with_scipy(b: bytes):
        """Read MATLAB bytes with scipy; not for MATLAB 7.3 and later (use hdf for those)."""
        from scipy.io import loadmat

        return loadmat(BytesIO(b))

    def read_matlab_bytes_with_h5py(b: bytes):
        import h5py

        return h5py.File(BytesIO(b), 'r')
