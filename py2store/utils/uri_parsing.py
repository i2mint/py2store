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