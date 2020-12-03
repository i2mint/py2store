from io import BytesIO
from py2store.stores.local_store import LocalBinaryStore
from py2store.trans import add_wrapper_method
from py2store.util import ModuleNotFoundErrorNiceMessage

# TODO: Offer some functionality based on builtins only (and compare performance to soundfile equivalent)
with ModuleNotFoundErrorNiceMessage():
    import soundfile as sf

# from py2store.mint import wraps, _empty_func

DFLT_DTYPE = "int16"
DFLT_FORMAT = "WAV"
DFLT_N_CHANNELS = 1

# TODO: Do some validation and smart defaults with these
dtype_from_sample_width = {
    1: "int16",
    2: "int16",
    3: "int32",
    4: "int32",
    8: "float64",
}

sample_width_for_soundfile_subtype = {
    "DOUBLE": 8,
    "FLOAT": 4,
    "G721_32": 4,
    "PCM_16": 2,
    "PCM_24": 3,
    "PCM_32": 4,
    "PCM_U8": 1,
}

# soundfile_signature not used yet, but intended for a future version of this module, that will use minting
# and signature injection instead of long copy pastes of
soundfile_signature = dict(
    dtype=DFLT_DTYPE, format=DFLT_FORMAT, subtype=None, endian=None
)


class SampleRateAssertionError(ValueError):
    ...


class ReadAudioFileMixin:
    read_kwargs = {}

    def _obj_of_data(self, data):
        return sf.read(BytesIO(data), **self.read_kwargs)


class PcmSerializationTrans:
    def __init__(
            self,
            sr,
            channels=DFLT_N_CHANNELS,
            dtype=DFLT_DTYPE,
            format="RAW",
            subtype="PCM_16",
            endian=None,
    ):
        assert isinstance(sr, int), "assert_sr must be an int"
        self.sr = sr
        self._rw_kwargs = dict(
            samplerate=sr,
            channels=channels,
            dtype=dtype,
            format=format,
            subtype=subtype,
            endian=endian,
        )

    def _obj_of_data(self, data):
        return sf.read(BytesIO(data), **self._rw_kwargs)[0]


@add_wrapper_method
class WfSrSerializationTrans:
    _read_format = DFLT_FORMAT
    _rw_kwargs = dict(dtype=DFLT_DTYPE, subtype=None, endian=None)

    def __init__(
            self, dtype=DFLT_DTYPE, format=DFLT_FORMAT, subtype=None, endian=None
    ):
        self._read_format = format
        self._rw_kwargs = dict(dtype=dtype, subtype=subtype, endian=endian)

    def _obj_of_data(self, data):
        return sf.read(BytesIO(data), **self._rw_kwargs)

    def _data_of_obj(self, obj):
        wf, sr = obj
        b = BytesIO()
        sf.write(b, wf, samplerate=sr, format=self._rw_kwargs)
        b.seek(0)
        return b.read()


@add_wrapper_method
class WfSerializationTrans(WfSrSerializationTrans):
    def __init__(
            self,
            assert_sr=None,
            dtype=DFLT_DTYPE,
            format=DFLT_FORMAT,
            subtype=None,
            endian=None,
    ):
        super().__init__(dtype, format, subtype, endian)
        self.assert_sr = assert_sr

    def _obj_of_data(self, data):
        wf, sr = super()._obj_of_data(data)
        if self.assert_sr is not None and sr != self.assert_sr:
            raise SampleRateAssertionError(
                f"{self.assert_sr} expected but I encountered {sr}"
            )
        return wf

    def _data_of_obj(self, obj):
        return super()._data_of_obj((obj, self.sr))


@add_wrapper_method
class WavSerializationTrans:
    _rw_kwargs = dict(format="WAV", subtype=None, endian=None)
    _read_kwargs = dict(dtype=DFLT_DTYPE)

    def __init__(
            self,
            assert_sr=None,
            dtype=DFLT_DTYPE,
            format="WAV",
            subtype=None,
            endian=None,
    ):
        if assert_sr is not None:
            assert isinstance(assert_sr, int), "assert_sr must be an int"
        self.assert_sr = assert_sr
        self._rw_kwargs = dict(format=format, subtype=subtype, endian=endian)
        self._read_kwargs = dict(dtype=dtype)

    def _obj_of_data(self, data):
        wf, sr = sf.read(BytesIO(data), **self._read_kwargs)
        if self.assert_sr != sr:
            if (
                    self.assert_sr is not None
            ):  # Putting None check here because less common, so more efficient on avg
                raise SampleRateAssertionError(
                    f"sr was {sr}, should be {self.assert_sr}"
                )
        return wf

    def _data_of_obj(self, obj):
        wf = obj
        b = BytesIO()
        sf.write(b, wf, samplerate=self.assert_sr, **self._rw_kwargs)
        b.seek(0)
        return b.read()


PcmSerializationMixin = PcmSerializationTrans  # alias for back-compatibility
WfSrSerializationMixin = WfSrSerializationTrans  # alias for back-compatibility
WavSerializationMixin = WavSerializationTrans  # alias for back-compatibility
WfSerializationMixin = WfSerializationTrans  # alias for back-compatibility

from py2store.base import Store


class WavLocalFileStore(WavSerializationTrans, LocalBinaryStore):
    def __init__(
            self,
            path_format,
            assert_sr=None,
            max_levels=None,
            dtype=DFLT_DTYPE,
            format="WAV",
            subtype=None,
            endian=None,
    ):
        LocalBinaryStore.__init__(self, path_format, max_levels)
        WavSerializationTrans.__init__(
            self,
            assert_sr=assert_sr,
            dtype=dtype,
            format=format,
            subtype=subtype,
            endian=endian,
        )


WavLocalFileStore2 = WavLocalFileStore  # back-compatibility alias

# Old WavLocalFileStore
# class WavLocalFileStore(Store):
#     def __init__(
#             self,
#             path_format,
#             assert_sr=None,
#             max_levels=None,
#             dtype=DFLT_DTYPE,
#             format="WAV",
#             subtype=None,
#             endian=None,
#     ):
#         persister = LocalBinaryStore(path_format, max_levels)
#         super().__init__(persister)
#         t = WavSerializationTrans(
#             assert_sr=assert_sr,
#             dtype=dtype,
#             format=format,
#             subtype=subtype,
#             endian=endian,
#         )
#         self._obj_of_data = t._obj_of_data


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
        return super()._id_of_key(
            self.sep.join(self.path_depth * ["{}"]).format(*k)
        )

    def _key_of_id(self, _id):
        raise DeprecationWarning("Deprecated")
        key = super()._key_of_id(_id)
        return tuple(key.split(self.sep))
