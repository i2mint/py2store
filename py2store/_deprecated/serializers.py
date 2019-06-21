########################################################################################################################
# Pickle Serializer
def mk_serializer_and_deserializer(rootdir: str, ext: str = '', protocol=None, fix_imports=True):
    import pickle
    def serial_of_obj(obj):
        return pickle.dumps(obj, protocol=protocol, fix_imports=fix_imports)

    def obj_of_serial(serial):
        return pickle.loads(serial, fix_imports=fix_imports)

    return serial_of_obj, obj_of_serial


########################################################################################################################
# File readers

def mk_file_reader_for_dflt(mode='r', **kwargs):
    """
    Makes a function that reads a json file, returning a dict.

    Signature is that of builtin open function.
    """

    def contents_of_file(filepath):
        """Reads a file.
        Generated from mk_file_reader_for_dflt"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        with open(filepath, mode=mode, **kwargs) as fp:
            return fp.read()

    return contents_of_file


# @wraps(sf.read)
def mk_file_reader_for_wav(dtype='int16', wf_only=True, assert_sr=None, **kwargs):
    """
    Makes a function that reads a wav file, returning a waveform (if wf_only=True) or a
    (waveform, samplerate) pair (if wf_only=False), asserting that the samplerate is equal to assert_sr, if given.
    By default, the dtype of the numpy array returned is int16, unless otherwise specified.
    All other kwargs are those from the signature of soundfile.read function, pasted below.
    """
    import soundfile as sf

    if assert_sr is not None:
        assert isinstance(assert_sr, int), "assert_sr must be an int"

    def contents_of_file(filepath):
        """Reads a wav file.
        Generated from mk_file_reader_for_wav"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        wf, sr = sf.read(filepath, dtype=dtype, **kwargs)
        if assert_sr is not None:
            assert sr == assert_sr, "Sample rate must be {} (was {})".format(assert_sr, sr)
        if wf_only:
            return wf
        else:
            return wf, sr

    contents_of_file._dtype = dtype
    contents_of_file._wf_only = wf_only
    contents_of_file._assert_sr = assert_sr
    contents_of_file._kwargs = kwargs
    return contents_of_file


def mk_file_reader_for_pcm(dtype='int16', wf_only=True, assert_sr=None, **kwargs):
    """
    Makes a function that reads a wav file, returning a waveform (if wf_only=True) or a
    (waveform, samplerate) pair (if wf_only=False), asserting that the samplerate is equal to assert_sr, if given.
    By default, the dtype of the numpy array returned is int16, unless otherwise specified.
    All other kwargs are those from the signature of soundfile.read function, pasted below.
    """
    import soundfile as sf

    if assert_sr is not None:
        assert isinstance(assert_sr, int), "assert_sr must be an int"

    def contents_of_file(filepath):
        """Reads a wav file.
        Generated from mk_file_reader_for_wav"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        wf, sr = sf.read(filepath, dtype=dtype, **kwargs)
        if assert_sr is not None:
            assert sr == assert_sr, "Sample rate must be {} (was {})".format(assert_sr, sr)
        if wf_only:
            return wf
        else:
            return wf, sr

    return contents_of_file


def mk_file_read_for_json(open_kwargs=None, cls=None, object_hook=None, parse_float=None,
                          parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
    """
    Makes a function that reads a json file, returning a dict.

    Signature is that of json.load.
    """
    import json

    if open_kwargs is None:
        open_kwargs = dict(mode='r', buffering=-1, encoding=None,
                           errors=None, newline=None, closefd=True, opener=None)

    def contents_of_file(filepath):
        """Reads a json file.
        Generated from mk_file_read_for_json"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        return json.load(open(filepath, **open_kwargs),
                         cls=cls, object_hook=object_hook, parse_float=parse_float,
                         parse_int=parse_int, parse_constant=parse_constant, object_pairs_hook=object_pairs_hook, **kw)

    return contents_of_file


def mk_file_read_for_pickle(open_kwargs=None, fix_imports=True, encoding='ASCII', errors='strict'):
    """Makes a function that reads a pickle file, returning a python object.

    Signature is that of pickle.load, pasted below:

    {}
    """

    import pickle

    if open_kwargs is None:
        open_kwargs = dict(mode='rb', buffering=-1, encoding=None,
                           errors=None, newline=None, closefd=True, opener=None)

    def contents_of_file(filepath):
        """Reads a pickle file.
        Generated from mk_file_read_for_pickle"""  # ({})""".format(
        # ', '.join(('{}={}'.format(k, v) for k, v in kwargs.items())))
        return pickle.load(open(filepath, **open_kwargs),
                           fix_imports=fix_imports, encoding=encoding, errors=errors)

    return contents_of_file


_file_reader_for_kind = {
    'dflt': mk_file_reader_for_dflt,
    'wav': mk_file_reader_for_wav,  # TODO: Deprecate and use wav_wf instead
    'wav_wf': mk_file_reader_for_wav,
    'json': mk_file_read_for_json,
    'pickle': mk_file_read_for_pickle
}


def mk_file_reader_func(kind: str = 'dflt', **kwargs):
    if kind is None:
        print("Possible kinds: {}".format(', '.join(_file_reader_for_kind)))
        return None
    return _file_reader_for_kind[kind](**kwargs)
