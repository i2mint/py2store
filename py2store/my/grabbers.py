"""
Grabbers: fetch an object from a key (a path or URL) and post-process it by kind.

A grabber is ``py2store.misc.get_obj`` with optional key and value transformations. The
``'ipython'`` grabber turns image, WAV audio and HTML bytes into the matching IPython display
objects, so that grabbing a file in a notebook shows it.

Main entry points:

- ``mk_grabber``: build a grabber from ``key_trans`` and ``val_trans`` functions
- ``grabber_for``: the ready-made grabbers by name (``'ipython'``)
- ``ipython_display_val_trans``: the value transformation behind the ``'ipython'`` grabber
"""
from functools import wraps
from io import BytesIO, StringIO

from py2store.misc import get_obj


def mk_grabber(*, key_trans=None, val_trans=None):
    """Make a function that fetches an object with ``get_obj``, with optional pre- and post-processing.

    Args:
        key_trans: Applied to the key before fetching (to strip whitespace or expand a path, say).
        val_trans: Applied as ``val_trans(value, key)`` to the fetched object before it is returned.

    Returns:
        A function ``grab(k, *args, **kwargs)`` that forwards ``*args`` and ``**kwargs`` to ``get_obj``.

    >>> import os, tempfile
    >>> path = os.path.join(tempfile.mkdtemp(), 'hello.txt')
    >>> _ = open(path, 'w').write('world')
    >>> grab = mk_grabber(key_trans=str.strip, val_trans=lambda v, k: v.upper())
    >>> grab(' ' + path + ' ')
    'WORLD'
    """
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
    """Wrap ``val`` (bytes) in an IPython display object by content: ``Image`` for image data, ``Audio`` for WAV data, ``HTML`` for HTML (by the ``key``'s extension when ``key`` is a string longer than 4 characters, else by a ``<!DOCTYPE html>`` start); anything else is returned unchanged.

    Requires IPython, and uses the ``imghdr`` module to detect images.
    """
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
    """The absolute path of ``path``, with a leading ``~`` expanded."""
    import os

    return os.path.abspath(os.path.expanduser(path))


DFLT_GRABBER = get_obj


def grabber_for(kind):
    """The ready-made grabber named ``kind``: ``'ipython'`` gives ``mk_grabber(val_trans=ipython_display_val_trans)``.

    Raises:
        ValueError: If ``kind`` is not a known grabber name.
    """
    if kind == 'ipython':
        return mk_grabber(val_trans=ipython_display_val_trans)
    else:
        raise ValueError(f'Unrecognized grabber kind: {kind}')
