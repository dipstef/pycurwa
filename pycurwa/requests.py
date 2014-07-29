# -*- coding: utf-8 -*-
from collections import OrderedDict
from time import time

from .curl import CurlMulti, CurlHandlesStatus
from .curl.error import CurlWriteError, CurlError, MissingHandle
from .request import CurlRequestBase


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

        return MultiRequestStatusCheck(request_completed, request_failed, status_time)

    def __len__(self):
        return len(self._request_handles)

    def __iter__(self):
        return iter(self._request_handles.values())


class MultiRequests(object):

    def __init__(self, curl=None):
        curl = curl or CurlMulti()
        self._requests = MultiRequestsBase(curl=curl)
        self._curl = curl
        self._handles_requests = OrderedDict()

    def _register(self, requests):
        for request in requests:
            self._requests.add(request)
            self._handles_requests[request.handle] = requests

    def _update(self):
        self._curl.execute()
        self._update_requests()
        self._curl.select(timeout=1)

    def _update_requests(self):
        status = self._requests.get_status()
        for request, request_status in self._group_by_request(status):
            request.update(request_status)
            #if request.is_completed():
            #    for request_handle in request:
            #        self._requests.close(request_handle)

    def _group_by_request(self, status):
        request_statuses = OrderedDict()

        for request in status.completed:
            request_group = self._handles_requests[request.handle]

            existing = request_statuses.get(request_group)
            if existing:
                existing.completed.append(request)
            else:
                request_statuses[request_group] = MultiRequestsStatus([request], [], status.check)

        for request in status.failed:
            request_group = self._handles_requests[request.handle]

            existing = request_statuses.get(request_group)
            if existing:
                existing.failed.append(request)
            else:
                request_statuses[request_group] = MultiRequestsStatus([], [request], status.check)

        return request_statuses.iteritems()


class MultiRequestRefresh(MultiRequests):

    def __init__(self, curl, refresh=0.5):
        super(MultiRequestRefresh, self).__init__(curl)
        self._refresh_rate = refresh
        self._last_update = 0

    def _update(self):
        now = time()
        status = self._update_status(now)
        return status

    def _update_status(self, now):
        if now - self._last_update >= self._refresh_rate:
            status = super(MultiRequestRefresh, self)._update()
            self._last_update = now
            return status


class MultiRequestsStatus(CurlHandlesStatus):
    def __init__(self, completed, failed, status_time=None):
        super(MultiRequestsStatus, self).__init__(completed, failed)
        self.check = status_time or time()


class MultiRequestStatusCheck(MultiRequestsStatus):
    def __init__(self, completed, failed, status_time=None):
        failed = [request for request in failed if request.failed()]

        errors = []
        for request in completed:
            status_error = request.get_status_error()
            if status_error:
                errors.append(request)
                failed.append(FailedRequest(request, status_error))

        completed = completed if not errors else [request for request in completed if not request in errors]

        super(MultiRequestStatusCheck, self).__init__(completed, failed, status_time)


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