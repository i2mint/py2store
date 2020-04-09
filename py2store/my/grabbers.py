from py2store import get_obj
from functools import wraps


def _has_wav_header(b):
    return len(b) >= 44 and b[:4] == b'RIFF' and b[8:12] == b'WAVE'


def ipython_display_val_trans(val):
    import imghdr
    from io import BytesIO
    image_type = imghdr.what(BytesIO(val))  # will be None if it's not an image
    if image_type is not None:
        from IPython.display import Image
        return Image(val)
    elif _has_wav_header(val):
        from IPython.display import Audio
        return Audio(val)
    else:
        return val


def fullpath(path):
    import os
    return os.path.abspath(os.path.expanduser(path))


def mk_grabber(*, key_trans=None, val_trans=None):
    @wraps(get_obj)
    def grab(k, *args, **kwargs):
        """just get_obj, but personalized with pre and/or post processing"""
        if key_trans is not None:
            k = key_trans(k)
        v = get_obj(k, *args, **kwargs)
        if val_trans is not None:
            return val_trans(v)
        else:
            return v

    return grab


DFLT_GRABBER = get_obj


def grabber_for(kind):
    if kind == 'ipython':
        return mk_grabber(val_trans=ipython_display_val_trans)
    else:
        raise ValueError(f"Unrecognized grabber kind: {kind}")
