# py2store.my.grabbers

Grabbers: fetch an object from a key (a path or URL) and post-process it by kind.

A grabber is `py2store.misc.get_obj` with optional key and value transformations. The
`'ipython'` grabber turns image, WAV audio and HTML bytes into the matching IPython display
objects, so that grabbing a file in a notebook shows it.

Main entry points:

- `mk_grabber`: build a grabber from `key_trans` and `val_trans` functions
- `grabber_for`: the ready-made grabbers by name (`'ipython'`)
- `ipython_display_val_trans`: the value transformation behind the `'ipython'` grabber

### Functions

| [`fullpath`](#py2store.my.grabbers.fullpath)(path)                         | The absolute path of `path`, with a leading `~` expanded.                                                                                                                                                                                                                     |
|-----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`grabber_for`](#py2store.my.grabbers.grabber_for)(kind)                      | The ready-made grabber named `kind`: `'ipython'` gives `mk_grabber(val_trans=ipython_display_val_trans)`.                                                                                                                                                                     |
| [`ipython_display_val_trans`](#py2store.my.grabbers.ipython_display_val_trans)(val[, key])  | Wrap `val` (bytes) in an IPython display object by content: `Image` for image data, `Audio` for WAV data, `HTML` for HTML (by the `key`'s extension when `key` is a string longer than 4 characters, else by a `<!DOCTYPE html>` start); anything else is returned unchanged. |
| [`mk_grabber`](#py2store.my.grabbers.mk_grabber)(\*[, key_trans, val_trans]) | Make a function that fetches an object with `get_obj`, with optional pre- and post-processing.                                                                                                                                                                                |

### py2store.my.grabbers.fullpath(path)

The absolute path of `path`, with a leading `~` expanded.

### py2store.my.grabbers.grabber_for(kind)

The ready-made grabber named `kind`: `'ipython'` gives `mk_grabber(val_trans=ipython_display_val_trans)`.

* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – If `kind` is not a known grabber name.

### py2store.my.grabbers.ipython_display_val_trans(val, key=None)

Wrap `val` (bytes) in an IPython display object by content: `Image` for image data, `Audio` for WAV data, `HTML` for HTML (by the `key`’s extension when `key` is a string longer than 4 characters, else by a `<!DOCTYPE html>` start); anything else is returned unchanged.

Requires IPython, and uses the `imghdr` module to detect images.

### py2store.my.grabbers.mk_grabber(, key_trans=None, val_trans=None)

Make a function that fetches an object with `get_obj`, with optional pre- and post-processing.

* **Parameters:**
  * **key_trans** – Applied to the key before fetching (to strip whitespace or expand a path, say).
  * **val_trans** – Applied as `val_trans(value, key)` to the fetched object before it is returned.
* **Returns:**
  A function `grab(k, *args, **kwargs)` that forwards `*args` and `**kwargs` to `get_obj`.

```pycon
>>> import os, tempfile
>>> path = os.path.join(tempfile.mkdtemp(), 'hello.txt')
>>> _ = open(path, 'w').write('world')
>>> grab = mk_grabber(key_trans=str.strip, val_trans=lambda v, k: v.upper())
>>> grab(' ' + path + ' ')
'WORLD'
```
