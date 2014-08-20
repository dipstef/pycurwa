import pycurl
from httpy.connection import is_disconnected

from httpy.connection.error import ConnectionRefused, SocketError, ConnectionTimeout, UnresolvableHost, NotConnected
from httpy.error import HttpServerSocketError, HttpError, InvalidRangeRequest, IncompleteRead


CurlError = pycurl.error


class PyCurlError(CurlError):

    def __init__(self, errno, message, *args, **kwargs):
        super(PyCurlError, self).__init__(errno, message, *args, **kwargs)
        self.curl_errno = self.args[0]
        self.curl_message = message


class CurlHttpError(HttpError, PyCurlError):
    def __init__(self, request, curl_error):
        super(CurlHttpError, self).__init__(request, curl_error)
        self.curl_errno = curl_error.curl_errno
        self.curl_message = curl_error.curl_message
        self.message = '%s: %s' % (self.__class__.__name__, self.curl_message)


class CurlHttpServerSocketError(HttpServerSocketError, PyCurlError):
    def __init__(self, request, error, curl_errno, curl_message):
        super(CurlHttpServerSocketError, self).__init__(request, error)
        self.curl_error = _get_error(curl_errno, curl_message)
        self.curl_errno = curl_errno
        self.curl_message = curl_message


_connection_errors = {pycurl.E_COULDNT_CONNECT,
                      pycurl.E_COULDNT_RESOLVE_HOST,
                      pycurl.E_OPERATION_TIMEDOUT,
                      pycurl.E_PARTIAL_FILE}

_by_errno = {
    pycurl.E_COULDNT_CONNECT: ConnectionRefused,
    pycurl.E_COULDNT_RESOLVE_HOST: UnresolvableHost,
    pycurl.E_OPERATION_TIMEDOUT: ConnectionTimeout,
    pycurl.E_HTTP_RANGE_ERROR: InvalidRangeRequest,
    pycurl.E_PARTIAL_FILE: IncompleteRead
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


def is_connection_error(errno):
    return errno in _connection_errors


def _get_error(errno, message):
    error_mapping = _by_errno.get(errno)
    return error_mapping(message) if error_mapping else _curl_error(errno, message)


class CurlNotConnected(CurlHttpServerSocketError):

    def __init__(self, request, curl_errno, curl_message):
        super(CurlNotConnected, self).__init__(request, NotConnected(), curl_errno, curl_message)

    def __new__(cls, request, *args):
        return super(CurlNotConnected, cls).__new__(cls, request, NotConnected(), *args)


class HttpCurlError(PyCurlError):

    def __new__(cls, request, errno, message, disconnected_check=None):
        if is_connection_error(errno):
            if disconnected_check is None:
                disconnected_check = is_disconnected()
            if disconnected_check:
                return CurlNotConnected(request, errno, message)

        error_mapping = _by_errno.get(errno)

        if error_mapping:
            if issubclass(error_mapping, SocketError):
                return CurlHttpServerSocketError(request, error_mapping(message), errno, message)
            elif issubclass(error_mapping, HttpError):
                error = error_mapping(request)
                error.message = error_mapping.__name__ + ': ' + message
                return error

        return CurlHttpError(request, _curl_error(errno, message))


class HandleUnknownError(HttpError):
    def __init__(self, request, error):
        super(HandleUnknownError, self).__init__(request, error)
        self.message += ' : %s, %s' % (error.__class__.__name__, str(error))


class HandleError(HttpError):
    def __new__(cls, request, error):
        if isinstance(error, CurlError):
            try:
                return PyCurlError(*error.args)
            except:
                return HandleUnknownError(request, error)
        return HandleUnknownError(request, error)