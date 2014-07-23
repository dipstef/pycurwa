#error 28 Timeout
#7 No Route To Host
import pycurl

from httpy.error import HttpServerSocketError


PyCurlError = pycurl.error


class CurlHttpServerError(HttpServerSocketError, PyCurlError):
    def __init__(self, request, error, *args, **kwargs):
        super(CurlHttpServerError, self).__init__(request, error, *args, **kwargs)