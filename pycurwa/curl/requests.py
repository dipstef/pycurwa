from collections import OrderedDict
from time import time

from . import CurlMulti, CurlHandlesStatus
from .error import CurlWriteError, CurlError, MissingHandle


class Requests(object):

    def __init__(self, requests=(), curl=None):
        self._curl = curl or CurlMulti()
        self._requests = RequestsDict()

        for request in requests:
            self.add(request)

    def add(self, request):
        self._curl.add_handle(request.handle)
        self._requests[request.handle] = request

    def remove(self, request):
        self._curl.remove_handle(request.handle)
        del self._requests[request.handle]

    def close(self, request):
        self.remove(request)
        request.close()

    def _get_request(self, handle):
        request = self._requests.get(handle)

        if not request:
            raise MissingHandle(handle)

        return request

    def get_status(self):
        return self._get_status(time())

    def _get_status(self, status_time):
        status = self._curl.get_status()

        while status.remaining:
            status = self._curl.get_status()

        request_completed = [self._get_request(handle) for handle in status.completed]
        request_failed = [CurlFailed(self._get_request(handle), errno, msg) for handle, errno, msg in status.failed]

        return RequestStatusCheck(request_completed, request_failed, status_time)

    def iterate_statuses(self):
        try:
            while self._has_active_requests():
                self._curl.execute()
                status = self.get_status()

                if status:
                    yield status

                self._curl.select(timeout=1)
        finally:
            self.terminate()

    def terminate(self):
        self._curl.close()

    def _has_active_requests(self):
        return bool(self._requests)

    def __len__(self):
        return len(self._requests)

    def __iter__(self):
        return iter(self._requests.values())


class RequestRefresh(object):

    def __init__(self, requests, refresh=0.5):
        self._requests = requests
        self._refresh_rate = refresh
        self._last_update = 0

    def get_status(self):
        now = time()
        if now - self._last_update >= self._refresh_rate:
            status = self._requests.get_status()
            self._last_update = now
        else:
            status = RequestsStatus([], [], now)

        return status

    def __getattr__(self, item):
        return getattr(self._requests, item)


class RequestsStatus(CurlHandlesStatus):
    def __init__(self, completed, failed, status_time=None):
        super(RequestsStatus, self).__init__(completed, failed)
        self.check = status_time or time()


class RequestStatusCheck(RequestsStatus):
    def __init__(self, completed, failed, status_time=None):
        failed = [request for request in failed if request.failed()]

        errors = []
        for request in completed:
            status_error = request.get_status_error()

            if status_error:
                errors.append(request)
                failed.append(FailedHandle(request, status_error))

        completed = completed if not errors else [request for request in completed if not request in errors]

        super(RequestStatusCheck, self).__init__(completed, failed, status_time)


class FailedHandle(object):

    def __init__(self, request, error):
        self._request = request
        self.error = error
        self.handle = request.handle

    def __getattr__(self, item):
        return getattr(self._request, item)

    def __repr__(self):
        return '%s: %s' % (repr(self._request), repr(self.error))


class CurlFailed(FailedHandle):
    def __init__(self, request, errno, msg):
        super(CurlFailed, self).__init__(request, CurlError(errno, msg))

    def is_write_error(self):
        return isinstance(self.error, CurlWriteError)

    def failed(self):
        return not self.is_write_error() or bool(self._request.get_status_error())


class RequestsDict(OrderedDict):

    def __init__(self, requests=()):
        super(RequestsDict, self).__init__(((request.handle, request) for request in requests))


class MultiRequests(object):

    def __init__(self, requests=None):
        self._requests = requests if requests is not None else Requests()
        self._handles_requests = OrderedDict()

    def add(self, requests):
        for request in requests:
            self._requests.add(request)
            self._handles_requests[request.handle] = requests

    def remove(self, requests):
        for request in requests:
            self._requests.remove(request)

    def iterate_statuses(self):
        return self._requests.iterate_statuses()

    def _close(self):
        self._requests.terminate()


class MultiRequestsRefresh(MultiRequests):
    def __init__(self, requests=None, refresh=0.5):
        request = Requests() if requests is None else requests
        super(MultiRequestsRefresh, self).__init__(RequestRefresh(request, refresh))