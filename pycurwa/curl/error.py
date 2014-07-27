import pycurl

from httpy import HttpRequest
from httpy.connection.error import ConnectionRefused, UnresolvableHost, SocketError, ConnectionTimeout
from httpy.error import HttpServerSocketError, HttpError, InvalidRangeRequest


class PyCurlError(pycurl.error):

    def __init__(self, errno, message, *args, **kwargs):
        super(PyCurlError, self).__init__(errno, message, *args, **kwargs)
        self.curl_errno = self.args[0]
        self.curl_message = message


class CurlHttpError(HttpError, PyCurlError):
    def __init__(self, request, curl_error):
        super(CurlHttpError, self).__init__(request, curl_error)
        self.curl_errno = curl_error.curl_errno
        self.curl_message = curl_error.curl_message


class CurlHttpServerSocketError(HttpServerSocketError, PyCurlError):
    def __init__(self, request, error, curl_errno, curl_message):
        super(CurlHttpServerSocketError, self).__init__(request, error)
        self.curl_errno = curl_errno
        self.curl_message = curl_message

_by_errno = {
    pycurl.E_COULDNT_CONNECT: ConnectionRefused,
    pycurl.E_COULDNT_RESOLVE_HOST: UnresolvableHost,
    pycurl.E_OPERATION_TIMEDOUT: ConnectionTimeout,
    pycurl.E_HTTP_RANGE_ERROR: InvalidRangeRequest
}


class CurlWriteError(PyCurlError):

    def __init__(self, message, *args, **kwargs):
        super(CurlWriteError, self).__init__(pycurl.E_WRITE_ERROR, message, *args, **kwargs)


_curl_errors = {
    pycurl.E_WRITE_ERROR: CurlWriteError
}


def _curl_error(errno, message):
    error_class = _curl_errors.get(errno)
    if error_class:
        return error_class(message)
    return PyCurlError(errno, message)


class CurlError(PyCurlError):

    def __new__(cls, errno, message):
        request = HttpRequest('GET', '')
        error_mapping = _by_errno.get(errno)

        if error_mapping:
            error = error_mapping(request, message) if issubclass(error_mapping, HttpError) else error_mapping(message)
            if isinstance(error, SocketError):
                return CurlHttpServerSocketError(request, error, errno, message)
        else:
            error = _curl_error(errno, message)

        return CurlHttpError(request, error)


class MissingHandle(Exception):
    def __init__(self, handle):
        super(MissingHandle, self).__init__('Handle not Found', handle)