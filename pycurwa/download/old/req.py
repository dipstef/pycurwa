# -*- coding: utf-8 -*-
from collections import OrderedDict
from time import time
from ...curl import CurlMulti, CurlMultiStatus
from ...curl.error import CurlWriteError, CurlError, MissingHandle
from ...request import CurlRequestBase


class MultiRequestsBase(object):

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

    def remove_all(self):
        for request in self._request_handles.values():
            self._remove(request)

    def close(self, request):
        self.remove(request)
        request.close()

    def close_all(self):
        for request in self._request_handles.values():
            self.close(request)

    def execute(self):
        return self._curl.execute()

    def get_status(self):
        return self._get_status(time())

    def _get_status(self, status_time):
        status = self._curl.get_status()

        request_completed = [self._get_request(handle) for handle in status.completed]
        request_failed = [CurlFailed(self._get_request(handle), errno, msg) for handle, errno, msg in status.failed]

        return MultiRequestStatusCheck(request_completed, request_failed, status.remaining, status_time)

    def _get_request(self, handle):
        request = self._request_handles.get(handle)

        if not request:
            raise MissingHandle(handle)

        return request

    def select(self, timeout=1):
        self._curl.select(timeout)

    def __len__(self):
        return len(self._request_handles)

    def __iter__(self):
        return iter(self._request_handles.values())


class MultiRequests(MultiRequestsBase):

    def get_status(self):
        status_time = time()

        status = self._get_status(status_time)

        while status.remaining:
            status = self._get_status(status_time)

        return status


class MultiRequestsStatuses(object):

    def __init__(self, curl):
        self._curl = curl

    def __iter__(self):
        try:
            while not self._done():
                self._curl.execute()
                status = self._get_status()

                if not self._done():
                    if status:
                        yield status

                    self._curl.select(timeout=1)
        finally:
            self._close()

    def _close(self):
        return self._curl.close()

    def _get_status(self):
        return self._curl.get_status()

    def _done(self):
        return False


class MultiRequestRefresh(MultiRequestsStatuses):

    def __init__(self, curl, refresh=0.5):
        super(MultiRequestRefresh, self).__init__(curl)
        self._refresh_rate = refresh
        self._last_update = 0

    def _get_status(self):
        now = time()
        status = self._get_status_refresh(now)
        return status

    def _get_status_refresh(self, now):
        if now - self._last_update >= self._refresh_rate:
            self._last_update = now
            return self._status()

    def _status(self):
        return self._curl.get_status()


class MultiRequestsStatus(CurlMultiStatus):
    def __init__(self, completed, failed, handles_remaining, status_time=None):
        super(MultiRequestsStatus, self).__init__(completed, failed, handles_remaining)
        self.check = status_time or time()


class MultiRequestStatusCheck(MultiRequestsStatus):
    def __init__(self, completed, failed, handles_remaining, status_time=None):
        failed = [request for request in failed if request.failed()]

        errors = []
        for request in completed:
            status_error = request.get_status_error()
            if status_error:
                errors.append(request)
                failed.append(FailedRequest(request, status_error))

        completed = completed if not errors else [request for request in completed if not request in errors]

        super(MultiRequestStatusCheck, self).__init__(completed, failed, handles_remaining, status_time)


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