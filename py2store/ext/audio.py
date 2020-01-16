from io import BytesIO
from py2store.stores.local_store import RelativePathFormatStoreEnforcingFormat
from py2store.stores.local_store import LocalBinaryStore

from py2store.util import ModuleNotFoundErrorNiceMessage

with ModuleNotFoundErrorNiceMessage():
    import soundfile as sf

# from py2store.mint import wraps, _empty_func

DFLT_DTYPE = 'int16'
DFLT_FORMAT = 'WAV'
DFLT_N_CHANNELS = 1

# soundfile_signature not used yet, but intended for a future version of this module, that will use minting
# and signature injection instead of long copy pastes of
soundfile_signature = dict(dtype=DFLT_DTYPE, format=DFLT_FORMAT, subtype=None, endian=None)


class SampleRateAssertionError(ValueError): ...


class ReadAudioFileMixin:
    read_kwargs = {}

    def _obj_of_data(self, data):
        return sf.read(BytesIO(data), **self.read_kwargs)


class PcmSerializationMixin:
    def __init__(self, sr, channels=DFLT_N_CHANNELS, dtype=DFLT_DTYPE, format='RAW', subtype='PCM_16', endian=None):
        assert isinstance(sr, int), "assert_sr must be an int"
        self.sr = sr
        self._rw_kwargs = dict(samplerate=sr, channels=channels,
                               dtype=dtype, format=format, subtype=subtype, endian=endian)

    def _obj_of_data(self, data):
        return sf.read(BytesIO(data), **self._rw_kwargs)[0]


class WfSrSerializationMixin:
    def __init__(self, dtype=DFLT_DTYPE, format=DFLT_FORMAT, subtype=None, endian=None):
        self._rw_kwargs = dict(dtype=dtype, format=format, subtype=subtype, endian=endian)

    def _obj_of_data(self, data):
        return sf.read(BytesIO(data), **self._rw_kwargs)

    def _data_of_obj(self, obj):
        wf, sr = obj
        b = BytesIO()
        sf.write(b, wf, samplerate=sr, format='WAV')
        b.seek(0)
        return b


class WavSerializationMixin:
    def __init__(self, assert_sr=None, dtype=DFLT_DTYPE, format=DFLT_FORMAT, subtype=None, endian=None):
        if assert_sr is not None:
            assert isinstance(assert_sr, int), "assert_sr must be an int"
        self.assert_sr = assert_sr
        self._rw_kwargs = dict(dtype=dtype, format=format, subtype=subtype, endian=endian)
        self._read_kwargs = dict(dtype=dtype)

    def _obj_of_data(self, data):
        wf, sr = sf.read(BytesIO(data), **self._read_kwargs)
        if self.assert_sr != sr:
            if self.assert_sr is not None:  # Putting None check here because less common, so more efficient on avg
                raise SampleRateAssertionError(f"sr was {sr}, should be {self.assert_sr}")
        return wf


from py2store.base import Store
from functools import wraps


class WavLocalFileStore(Store):
    @wraps(LocalBinaryStore.__init__)
    def __init__(self, path_format, assert_sr=None,
                 dtype=DFLT_DTYPE, format='WAV', subtype=None, endian=None):
        persister = LocalBinaryStore(path_format)
        super().__init__(persister)
        t = WavSerializationMixin(assert_sr=assert_sr, dtype=dtype, format=format,
                                  subtype=subtype, endian=endian)
        self._obj_of_data = t._obj_of_data


class WavLocalFileStore2(WavSerializationMixin, LocalBinaryStore):
    def __init__(self, path_format, assert_sr=None,
                 dtype=DFLT_DTYPE, format='WAV', subtype=None, endian=None):
        RelativePathFormatStoreEnforcingFormat.__init__(self, path_format)
        WavSerializationMixin.__init__(self, assert_sr=assert_sr, dtype=dtype, format=format,
                                       subtype=subtype, endian=endian)


# class WfSrLocalFileStore(LocalBinaryStore):
# """"""
#     def _obj_of_data(self, data):
#         return data
#         return sf.read(BytesIO(data))


from py2store.stores.local_store import MakeMissingDirsStoreMixin
import os


class PcmSourceSessionBlockStore(MakeMissingDirsStoreMixin, LocalBinaryStore):
    sep = os.path.sep
    path_depth = 3

    def _id_of_key(self, k):
        raise DeprecationWarning("Deprecated")
        assert len(k) == self.path_depth
        return super()._id_of_key(self.sep.join(self.path_depth * ['{}']).format(*k))

    def _key_of_id(self, _id):
        raise DeprecationWarning("Deprecated")
        key = super()._key_of_id(_id)
        return tuple(key.split(self.sep))
