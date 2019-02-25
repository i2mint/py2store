import soundfile as sf
from io import BytesIO

DFLT_SUBTYPE = 'PCM_16'
DFLT_WF_DTYPE = 'int16'


def write_to_wav_file(filepath, wf, sr, subtype=DFLT_SUBTYPE):
    """
    Write a waveform to a wav file.
    :param filepath: File path
    :param wf: waveform (assumed to be int16 by default)
    :param sr: sample rate
    :param subtype: 'PCM_16' by default
    :return: None
    >>> import numpy as np
    >>> import os
    >>> test_file = '__test.wav'
    >>> write = write_to_wav_file
    >>> read = read_wav_file
    >>> wf = np.random.randint(-30000, 30000, 20000, dtype='int16')
    >>> sr = 44100
    >>> write(test_file, wf, sr)
    >>> wff, srr = read(test_file)
    >>> assert srr == sr
    >>> assert all(wff == wf)
    >>> os.remove(test_file)
    """
    sf.write(filepath, wf, sr, subtype=subtype, format='WAV')


def read_wav_file(filepath, dtype=DFLT_WF_DTYPE):
    """
    Read a wav file.
    :param filepath: File path
    :param dtype: Type for samples. int16 by default
    :return: wf, sr (waveform, sample rate)
    >>> import numpy as np
    >>> import os
    >>> test_file = '__test.wav'
    >>> write = write_to_wav_file
    >>> read = read_wav_file
    >>> wf = np.random.randint(-30000, 30000, 20000, dtype='int16')
    >>> sr = 44100
    >>> write(test_file, wf, sr)
    >>> wff, srr = read(test_file)
    >>> assert srr == sr
    >>> assert all(wff == wf)
    >>> os.remove(test_file)
    """
    return sf.read(filepath, dtype=dtype)


########################################################################################################################
# Three function that represent audio as wav: as BytesIO, memoryview, and bytes

def _wav_bytesio_of_wfsr(wf, sr, subtype=DFLT_SUBTYPE) -> BytesIO:
    """
    Get the memoryview of a wav representation of audio wavform (and sample rate).
    :param wf: waveform (assumed to be int16 by default)
    :param sr: sample rate
    :param subtype: 'PCM_16' by default
    :return: wav bytes (memoryview)
    >>> import numpy as np
    >>> write = _wav_bytesio_of_wfsr
    >>> read = lambda source: sf.read(source, dtype='int16')
    >>> wf = np.random.randint(-30000, 30000, 20000, dtype='int16')
    >>> sr = 44100
    >>> test_file = write(wf, sr)
    >>> _ = test_file.seek(0)
    >>> wff, srr = read(test_file)
    >>> assert srr == sr
    >>> assert all(wff == wf)
    """
    bytes_io = BytesIO()
    sf.write(bytes_io, wf, sr, subtype=subtype, format='WAV')
    return bytes_io


def _wav_memoryview_of_wfsr(wf, sr, subtype=DFLT_SUBTYPE) -> memoryview:
    """
    Get the memoryview of a wav representation of audio wavform (and sample rate).
    :param wf: waveform (assumed to be int16 by default)
    :param sr: sample rate
    :param subtype: 'PCM_16' by default
    :return: wav bytes (memoryview)
    >>> import numpy as np
    >>> write = _wav_memoryview_of_wfsr
    >>> read = wfsr_of_wav_bytes
    >>> wf = np.random.randint(-30000, 30000, 20000, dtype='int16')
    >>> sr = 44100
    >>> test_file = write(wf, sr)
    >>> wff, srr = read(test_file)
    >>> assert srr == sr
    >>> assert all(wff == wf)
    """
    return _wav_bytesio_of_wfsr(wf, sr, subtype).getbuffer()


def wav_bytes_of_wfsr(wf, sr, subtype=DFLT_SUBTYPE) -> bytes:
    """
    Get the bytes of a wav representation of audio wavform (and sample rate).
    :param wf: waveform (assumed to be int16 by default)
    :param sr: sample rate
    :param subtype: 'PCM_16' by default
    :return: wav bytes (memoryview)
    >>> import numpy as np
    >>> write = wav_bytes_of_wfsr
    >>> read = wfsr_of_wav_bytes
    >>> wf = np.random.randint(-30000, 30000, 20000, dtype='int16')
    >>> sr = 44100
    >>> test_file = write(wf, sr)
    >>> wff, srr = read(test_file)
    >>> assert srr == sr
    >>> assert all(wff == wf)
    """
    return bytes(_wav_memoryview_of_wfsr(wf, sr, subtype))


########################################################################################################################
# Reading wav bytes to resolve (wf, sr)

def wfsr_of_wav_bytes(wav_bytes: bytes, dtype=DFLT_WF_DTYPE):
    """
    Get the waveform and sample rate of wav bytes.
    :param wav_bytes: the bytes (or memoryview) of a wav representation of audio
    :param dtype: Type for samples. int16 by default
    :return: wf, sr (waveform, sample rate)
    >>> import numpy as np
    >>> write = wav_bytes_of_wfsr
    >>> read = wfsr_of_wav_bytes
    >>> wf = np.random.randint(-30000, 30000, 20000, dtype='int16')
    >>> sr = 44100
    >>> test_file = write(wf, sr)
    >>> wff, srr = read(test_file)
    >>> assert srr == sr
    >>> assert all(wff == wf)
    """
    return sf.read(BytesIO(wav_bytes), dtype=dtype)


########################################################################################################################
# Test functions

def _write_to_wav_file_through_bytes(filepath, wf, sr, subtype=DFLT_SUBTYPE):
    """
    Write to wav file, but using wav_bytes_of_wfsr to get bytes, then writing them to file.
    This function was only meant for testing.
    Writing directly to file is ~20% faster.
    >>> import numpy as np
    >>> import os
    >>> test_file = '__test.wav'
    >>> write = _write_to_wav_file_through_bytes
    >>> read = _read_wav_file_through_bytes
    >>> wf = np.random.randint(-30000, 30000, 20000, dtype='int16')
    >>> sr = 44100
    >>> write(test_file, wf, sr)
    >>> wff, srr = read(test_file)
    >>> assert srr == sr
    >>> assert all(wff == wf)
    >>> os.remove(test_file)
    """
    b = wav_bytes_of_wfsr(wf, sr, subtype=subtype)
    with open(filepath, 'wb') as fp:
        fp.write(b)


def _read_wav_file_through_bytes(filepath):
    """
    Read a wav file, but first reading in byte content, then using wfsr_of_wav_bytes to get (wf, sr).
    This function was only meant for testing.
    Reading directly to file is ~35% faster.
    >>> import numpy as np
    >>> import os
    >>> test_file = '__test.wav'
    >>> write = _write_to_wav_file_through_bytes
    >>> read = _read_wav_file_through_bytes
    >>> wf = np.random.randint(-30000, 30000, 20000, dtype='int16')
    >>> sr = 44100
    >>> write(test_file, wf, sr)
    >>> wff, srr = read(test_file)
    >>> assert srr == sr
    >>> assert all(wff == wf)
    >>> os.remove(test_file)
    """
    with open(filepath, 'rb') as fp:
        b = fp.read()
    return wfsr_of_wav_bytes(b)
