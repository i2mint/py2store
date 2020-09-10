from warnings import warn

warn(
    "dropbox_w_requests doesn't depend on requests anymore, so has been moved to dropbox_w_urllib"
)

# raise DeprecationWarning("dropbox_w_requests doesn't depend on requests anymore, so has been moved to dropbox_w_urllib")

from py2store.persisters.dropbox_w_urllib import *
