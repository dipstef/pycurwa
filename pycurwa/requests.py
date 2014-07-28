# -*- coding: utf-8 -*-
from abc import abstractmethod
from collections import OrderedDict
from time import time
from .curl import CurlMulti
from .curl.error import CurlWriteError, CurlError, MissingHandle
from .error import BadHeader
from .request import CurlBodyRequest


class MultiRequests(object):

    def __init__(self, requests=(), curl=None):
        self._curl = curl or CurlMulti()
        self._request_handles = RequestsDict()

        for request in requests:
            self.add(request)

    def add(self, request):
        assert isinstance(request, CurlBodyRequest)
        self._add(request)

    def _add(self, request):
        self._curl.add_handle(request.handle)
        self._request_handles[request.handle] = request

    def remove(self, request):
        assert isinstance(request, CurlBodyRequest)
        self._remove(request)

    def _remove(self, request):
        self._curl.remove_handle(request.handle)
        del self._request_handles[request.handle]

    def close(self, request):
        self.remove(request)
        request.close()

    def _close_all(self):
        for request in self._request_handles.values():
            self.close(request)

    def execute(self):
        return self._curl.execute()

    def get_status(self):
        status = self._get_status(status_time=time())

        return status

    def _get_status(self, status_time):
        handles_remaining, curl_completed, curl_failed = self._curl.info_read()

        request_completed = [self._get_request(handle) for handle in curl_completed]
        request_failed = [(self._get_request(handle), CurlError(errno, msg)) for handle, errno, msg in curl_failed]

        status = MultiRequestsStatus(status_time, request_completed, request_failed, handles_remaining)
        return _check_status_codes(status)

    def _get_request(self, handle):
        request = self._request_handles.get(handle)

        if not request:
            raise MissingHandle(handle)

        return request

    def _select(self, timeout=1):
        self._curl.select(timeout)

    def __len__(self):
        return len(self._request_handles)

    def __iter__(self):
        return iter(self._request_handles.values())


class MultiRequestsStatuses(MultiRequests):

    def __init__(self, requests=(), curl=None):
        super(MultiRequestsStatuses, self).__init__(requests, curl)
        self._last_check = None
        self._last_status = None

    def iterate_statuses(self):
        try:
            while not self._done():
                self.execute()

                status = self.get_status()

                if not self._done():
                    if status != self._last_status:
                        self._last_status = status

                        yield status

                    self._select(timeout=1)
        finally:
            self._close_all()

    def get_status(self):
        self._last_check = time()

        status = self._get_status(status_time=self._last_check)

        while status.handles_remaining:
            status = self._get_status(status_time=self._last_check)

        return status

    def _done(self):
        return False


class MultiRequestsStatus(object):

    def __init__(self, check, completed, failed, handles_remaining):
        self.check = check
        self.completed = completed
        self.failed = failed
        self.handles_remaining = handles_remaining


class RequestsDict(OrderedDict):
    def __init__(self, requests=()):
        super(RequestsDict, self).__init__(((request.handle, request) for request in requests))


def _check_status_codes(status):
    completed, failed = [], []

    for request in status.completed:
        try:
            request.verify_header()
            completed.append(request)
        except BadHeader, e:
            failed.append((request, e))

    for request, error in status.failed:
        if isinstance(error, CurlWriteError):
            # double check header
            try:
                request.verify_header()
                #completed.append(request)
            except BadHeader:
                failed.append((request, error))

    return MultiRequestsStatus(status.check, completed, failed, status.handles_remaining)