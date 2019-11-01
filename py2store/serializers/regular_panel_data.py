"""Serialization for regular panel data (audio, regular-tick time-series, etc.).
"""

import numpy as np
import soundfile as sf
from io import BytesIO


class WrongSampleRate(ValueError):
    """ To be raised when the sample rate is not the one that's expected. """
    pass


class WrongSerializationParams(ValueError):
    pass


def mk_reader_and_writer(sr: int, format='RAW', subtype='PCM_16', dtype='int16', channels: int = 1,
                         endian=None, always_2d=False):
    """Makes a (bijective) pair of numerical arrays serializer and deserializer functions.
    A function returning bijective panel data reader and writer functions with simple interfaces (all parametrizations
    are fixed): `read(source)` and `write(source, data)`.
    The writer and reader are essentially matrix (or array) serializers and deserializers respectively,
    using the same serialization protocols as waveform (into PCM, WAV, etc.)

    Args:
        sr: Sample rate. When the serialization format handles this information (e.g. WAV format)
            the sample rate is actually written (in WAV, in the header bytes), and asserted on reads
            (that is, if you read a WAV file that doesn't have that exact sample rate in it's header, a
            WrongSampleRate error will be raised.
            When the serialization format doesn't (e.g. RAW format (a.k.a. PCM)), it is ignored both on reads and writes
        format: 'RAW', 'WAV' and others (see soundfile.available_formats() for a full list)
        subtype: 'FLOAT', 'PCM_16' and others (see soundfile.available_subtypes() for a full list)
        dtype: 'float64', 'float32', 'int32', 'int16'
        channels: Number of channels (should equal the number of columns of the data matrices that will be
            serialized -- or 1 if the data is flat)
        endian: see soundfile documentation ({'FILE', 'LITTLE', 'BIG', 'CPU'}, sometimes optional)
        always_2d: By default, reading a mono sound file will return a one-dimensional array. With always_2d=True,
            data is always returned as a two-dimensional array, even if the data has only one channel.

    Returns:
        read(k), write(k, v) functions

    >>> n_channels, dtype = 1, 'float64'
    >>> read, write = mk_reader_and_writer(sr=44100, channels=n_channels, subtype='FLOAT', format='RAW', dtype=dtype)
    >>> data = _random_matrix(n_channels=n_channels, dtype=dtype)
    >>> _test_data_write_read(data, writer=write, reader=read)

    >>> n_channels, dtype = 4, 'int16'
    >>> read, write = mk_reader_and_writer(sr=2, channels=n_channels, subtype='PCM_16', format='RAW', dtype=dtype)
    >>> data = _random_matrix(n_channels=n_channels, dtype=dtype)
    >>> _test_data_write_read(data, writer=write, reader=read)
    """
    if not sf.check_format(format, subtype, endian):
        raise WrongSerializationParams(f"Not a valid combo: format={format}, subtype={subtype}, endian={endian}")

    subtype = subtype or sf.default_subtype(format)

    if format == 'RAW':
        def read(k):
            wf, _ = sf.read(k, samplerate=sr, channels=channels, format=format, subtype=subtype,
                            dtype=dtype, endian=endian, always_2d=always_2d)
            return wf
    else:
        def read(k):
            wf, sr_read = sf.read(k, dtype=dtype, always_2d=always_2d)
            if sr != sr_read:
                raise WrongSampleRate(f"Sample rate was {sr_read}: Expected {sr}")
            return wf

    def write(k, v):
        return sf.write(k, v, samplerate=sr, format=format, subtype=subtype, endian=endian)

    # add some attributes to the functions, for diagnosis purposes
    read.sr = sr
    read.dtype = dtype
    read.format = format
    write.sr = sr
    write.format = format
    write.subtype = subtype

    return read, write


# TODO: Make it pytest compliant (problem with fixture)
def _test_data_write_read(data, writer, reader):
    b = BytesIO()
    writer(b, data)
    b.seek(0)  # rewind
    read_data = reader(b)
    if isinstance(read_data, tuple):
        read_data, read_sr = read_data
    assert np.allclose(read_data, data), "np.allclose(read_data, data)"
    # assert read_sr == sr, 'read_sr == sr'


def _random_matrix(n_samples=100, n_channels=1, value_range=(-2000, 2000), dtype='float64'):
    """
    Make a random matrix with n_samples rows and n_channels columns, with numbers drawn randomly from
    the value_range interval
    Args:
        n_samples: number of rows in the matrix
        n_channels: number of columns in the matrix (if n_channels=1, the function will output a flat array)
        value_range: the range to pick from

    Returns:
        a matrix (i.e. array of arrays) or a flat array (if n_channels==1).
    """

    if isinstance(value_range, (int, float)):
        interval_length = value_range
        value_range = (-interval_length / 2, interval_length / 2)
    else:
        interval_length = value_range[1] - value_range[0]

    data = (np.random.rand(n_samples, n_channels) * interval_length) + value_range[0]

    if n_channels == 1:
        data = np.ravel(data)

    return data.astype(dtype)


def _random_data_and_serialization_params(
        n_samples=100, n_channels=1, value_range=(-2000, 2000), dtype='float64'):
    """ Get random data and serialization params (i.e. how to map to bytes)"""
    raise NotImplementedError("Not implemented yet")


if __name__ == '__main__':
    n_channels, dtype = 1, 'float64'
    read, write = mk_reader_and_writer(sr=44100, channels=n_channels, subtype='FLOAT', format='RAW', dtype=dtype)
    data = _random_matrix(n_channels=n_channels, dtype=dtype)
    _test_data_write_read(data, writer=write, reader=read)

    n_channels, dtype = 1, 'int16'
    read, write = mk_reader_and_writer(sr=44100, channels=n_channels, subtype='PCM_16', format='RAW', dtype=dtype)
    data = _random_matrix(n_channels=n_channels, dtype=dtype)
    _test_data_write_read(data, writer=write, reader=read)

    n_channels, dtype = 1024, 'float32'
    read, write = mk_reader_and_writer(sr=10, channels=n_channels, subtype='FLOAT', format='RAW', dtype=dtype)
    data = _random_matrix(n_channels=n_channels, dtype=dtype)
    _test_data_write_read(data, writer=write, reader=read)

    n_channels = int(2 ** 10 - 1)  # one more would be too much for format='WAV'
    read, write = mk_reader_and_writer(sr=1, channels=n_channels, subtype='FLOAT', format='WAV')
    data = _random_matrix(n_channels=n_channels)
    _test_data_write_read(data, writer=write, reader=read)
