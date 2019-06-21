from io import BytesIO
import soundfile as sf
from py2store.stores.local_store import RelativePathFormatStoreEnforcingFormat


class SampleRateAssertionError(ValueError):
    pass


class WfSerializatoinMixin:
    assert_sr = None

    def _obj_of_data(self, data):
        wf, sr = sf.read(BytesIO(data), dtype='int16')
        if self.assert_sr != sr:
            raise SampleRateAssertionError(f"sr was {sr}, should be {self.assert_sr}")
        return wf


class WfStore(RelativePathFormatStoreEnforcingFormat, WfSerializatoinMixin):
    def __init__(self, assert_sr, path_format, delete=True):
        super().__init__(path_format, read='b', write='b', delete=delete)
        self.assert_sr = assert_sr
