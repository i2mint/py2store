"""
define stores (and functions) so they give you data as you want it, depending on the extension
"""
from functools import wraps
from io import BytesIO, StringIO

from py2store.misc import get_obj


def mk_grabber(*, key_trans=None, val_trans=None):
    @wraps(get_obj)
    def grab(k, *args, **kwargs):
        """just get_obj, but personalized with pre and/or post processing"""
        if key_trans is not None:
            k = key_trans(k)
        v = get_obj(k, *args, **kwargs)
        if val_trans is not None:
            return val_trans(v, k)
        else:
            return v

    return grab


def _read_line_and_rewind(readable):
    comebackto = readable.tell()
    line = readable.readline()
    readable.seek(comebackto)
    return line


def _has_wav_header(b):
    return len(b) >= 44 and b[:4] == b'RIFF' and b[8:12] == b'WAVE'


def _is_html(x, key=None):
    if isinstance(key, str) and len(key) > 4:
        if 'htm' in key[-4:]:
            return True
    else:
        if isinstance(x, (BytesIO, StringIO)):
            x = _read_line_and_rewind
        if isinstance(x, str):
            return x[:15] == '<!DOCTYPE html>'
        elif isinstance(x, bytes):
            return x[:15] == b'<!DOCTYPE html>'
    return False  # if not returned before


def ipython_display_val_trans(val, key=None):
    from IPython.display import Image, Audio, HTML
    import imghdr

    image_type = imghdr.what(BytesIO(val))  # will be None if it's not an image
    if image_type is not None:
        return Image(val)
    elif _has_wav_header(val):
        return Audio(val)
    elif _is_html(val, key):
        if isinstance(val, bytes):
            val = val.decode()
        return HTML(val)
    else:
        return val


def fullpath(path):
    import os

    return os.path.abspath(os.path.expanduser(path))


DFLT_GRABBER = get_obj


def grabber_for(kind):
    if kind == 'ipython':
        return mk_grabber(val_trans=ipython_display_val_trans)
    else:
        raise ValueError(f'Unrecognized grabber kind: {kind}')
