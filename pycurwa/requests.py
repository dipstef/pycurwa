# -*- coding: utf-8 -*-
from collections import OrderedDict
from time import time

from .curl import CurlMulti, CurlHandlesStatus
from .curl.error import CurlWriteError, CurlError, MissingHandle
from .request import CurlRequestBase


class Requests(object):

    def __init__(self, requests=(), curl=None):
        self._curl = curl or CurlMulti()
        self._request_handles = RequestsDict()

        for request in requests:
            self.add(request)

    def add(self, request):
        assert isinstance(request, CurlRequestBase)
        self._add(request)

    def _add(self, request):
        self._curl.add_handle(request.handle)
        self._request_handles[request.handle] = request

    def remove(self, request):
        assert isinstance(request, CurlRequestBase)
        self._remove(request)

    def _remove(self, request):
        self._curl.remove_handle(request.handle)
        del self._request_handles[request.handle]

    def close(self, request):
        self.remove(request)
        request.close()

    def _get_request(self, handle):
        request = self._request_handles.get(handle)

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

    def execute(self):
        return self._curl.execute()

    def select(self, timeout=None):
        return self._curl.select(timeout)

    def terminate(self):
        self._curl.close()

    def __len__(self):
        return len(self._request_handles)

    def __iter__(self):
        return iter(self._request_handles.values())


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

    def _get_status(self):
        status = self._requests.get_status()
        return status

    def iterate_statuses(self):
        try:
            while self._has_active_requests():
                self._requests.execute()
                status = self._get_status()

                if status:
                    yield status

                self._requests.select(timeout=1)
        finally:
            self._close()

    def _has_active_requests(self):
        return bool(self._requests)

    def _close(self):
        self._requests.terminate()


class MultiRequestRefresh(MultiRequests):

    def __init__(self, refresh=0.5, requests=None):
        super(MultiRequestRefresh, self).__init__(requests)
        self._refresh_rate = refresh
        self._last_update = 0

    def _get_status(self):
        now = time()
        if now - self._last_update >= self._refresh_rate:
            status = super(MultiRequestRefresh, self)._get_status()
            self._last_update = now
        else:
            status = RequestsStatus([], [], now)

        return status


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
                failed.append(FailedRequest(request, status_error))

        completed = completed if not errors else [request for request in completed if not request in errors]

        super(RequestStatusCheck, self).__init__(completed, failed, status_time)


class FailedRequest(object):

    def __init__(self, request, error):
        self._request = request
        self.error = error
        self.handle = request.handle

    def __getattr__(self, item):
        return getattr(self._request, item)

    def __repr__(self):
        return '%s: %s' % (repr(self._request), repr(self.error))


class CurlFailed(FailedRequest):
    def __init__(self, request, errno, msg):
        super(CurlFailed, self).__init__(request, CurlError(errno, msg))

    def is_write_error(self):
        return isinstance(self.error, CurlWriteError)

    def failed(self):
        return not self.is_write_error() or bool(self._request.get_status_error())


class RequestsDict(OrderedDict):

    def __init__(self, requests=()):
        super(RequestsDict, self).__init__(((request.handle, request) for request in requests))