from collections import OrderedDict
from time import time

from httpy.connection.error import NotConnected
from httpy.error import error_status, HttpStatusError
from procol.console import print_err, print_err_trace

from . import CurlHandlesStatus
from .error import CurlWriteError, HttpCurlError, HandleError, is_connection_error


class CurlRequests(object):

    def __init__(self, curl):
        self._curl = curl
        self._requests = OrderedDict()

    def _get_status(self, now):
        status = self._curl.get_status()

        while status.remaining:
            status = self._curl.get_status()

        completed, failed = [], []

        for handle in status.completed:
            request = self._get_request(handle)
            if request:
                error = _get_response_status_error(request)
                if error:
                    failed.append(FailedHandle(request, error))
                else:
                    completed.append(request)

        disconnected_check = None
        for handle, errno, msg in status.failed:
            request = self._requests.get(handle)
            if request:
                error = HttpCurlError(request, errno, msg, disconnected_check)
                if is_connection_error(errno) and disconnected_check is None:
                    disconnected_check = isinstance(error, NotConnected)

                failed.append(FailedHandle(request, error))

        return RequestsStatus(completed, failed, now)

    def _get_request(self, handle):
        request = self._requests.get(handle)

        if not request:
            #should never happen
            print_err('Cant locate request for handle ' % repr(handle))

            handle.close()
            self._curl.remove_handle(handle)

        return request


class RequestsStatus(CurlHandlesStatus):
    def __init__(self, completed, failed, status_time=None):
        super(RequestsStatus, self).__init__(completed, failed)
        self.check = status_time or time()


class FailedHandle(object):

    def __init__(self, request, error):
        self._request = request
        self.error = error
        self.handle = request.handle

    def __getattr__(self, item):
        return getattr(self._request, item)

    def __repr__(self):
        return '%s: %s' % (repr(self._request), repr(self.error))

    def is_write_error(self):
        return isinstance(self.error, CurlWriteError)

    def is_not_found(self):
        response = self._request.get_response()
        status_code = response.status
        return bool(status_code) and status_code == 404


def _get_response_status_error(request):
    response = request.get_response()
    try:
        status_code = response.get_status()
        if status_code in error_status:
            return HttpStatusError(request, status_code)
    except BaseException, error:
        #should not happen as handle should be still opened
        print_err_trace('Handle closed?')
        return HandleError(request, error)