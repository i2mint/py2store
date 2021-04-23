"""
utils to work with URIs
"""
from urllib.parse import urlsplit


def parse_uri(uri):
    """
    Parses DB URI string into a dict of params.
    :param uri: string formatted as: "scheme://username:password@host:port/database"
    :return: a dict with these params parsed.
    """
    splitted_uri = urlsplit(uri)

    if splitted_uri.path.startswith('/'):
        path = splitted_uri.path[1:]
    else:
        path = ''

    return {
        'scheme': splitted_uri.scheme,
        'database': path,
        'username': splitted_uri.username,
        'password': splitted_uri.password,
        'hostname': splitted_uri.hostname,
        'port': splitted_uri.port,
    }


def build_uri(
    scheme,
    database='',  # TODO: Change name: Not always a database
    username=None,
    password=None,
    host='localhost',
    port=None,
):
    """
    Reverse of `parse_uri` function.
    Builds a URI string from provided params.
    """
    port_ = f':{port}' if port else ''
    uri = f'{scheme}://{username}:{password}@{host}{port_}/{database}'
    return uri


import string
from py2store.signatures import set_signature_of_func

str_formatter = string.Formatter()


def mk_str_making_func(
    str_format: str, input_trans=None, method=False, module=None, name=None
):
    fields = tuple(
        filter(None, (x[1] for x in str_formatter.parse(str_format)))
    )  # TODO: validate
    n_fields = len(fields)

    if method:

        def _mk(self, *args, **kwargs):
            n = len(args) + len(kwargs)
            if n > n_fields:
                raise ValueError(
                    f'You have too many arguments: (args, kwargs) is ({args}, {kwargs})'
                )
            elif n < n_fields:
                raise ValueError(
                    f'You have too few arguments: (args, kwargs) is ({args}, {kwargs})'
                )
            kwargs = dict({k: v for k, v in zip(fields, args)}, **kwargs)
            if input_trans is not None:
                kwargs = input_trans(**kwargs)
            return str_format.format(**kwargs)

        set_signature_of_func(_mk, ['self'] + list(fields))
    else:

        def _mk(*args, **kwargs):
            n = len(args) + len(kwargs)
            if n > n_fields:
                raise ValueError(
                    f'You have too many arguments: (args, kwargs) is ({args}, {kwargs})'
                )
            elif n < n_fields:
                raise ValueError(
                    f'You have too few arguments: (args, kwargs) is ({args}, {kwargs})'
                )
            kwargs = dict({k: v for k, v in zip(fields, args)}, **kwargs)
            if input_trans is not None:
                kwargs = input_trans(**kwargs)
            return str_format.format(**kwargs)

        set_signature_of_func(_mk, fields)

    if module is not None:
        _mk.__module__ = module

    if name is not None:
        _mk.__qualname__ = name

    return _mk
