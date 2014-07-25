# -*- coding: utf-8 -*-
from abc import abstractmethod
from .curl import CurlMulti
from .curl.error import CurlWriteError, CurlError, MissingHandle
from .error import BadHeader
from .request import CurlBodyRequest


class MultiRequestsBase(object):

    def __init__(self):
        self._curl = CurlMulti()

    def add(self, request):
        assert isinstance(request, CurlBodyRequest)
        self._curl.add_handle(request.handle)
        self._add_request(request)

    @abstractmethod
    def _add_request(self, request):
        pass

    def remove(self, request):
        assert isinstance(request, CurlBodyRequest)
        self._curl.remove_handle(request.handle)
        self._remove_request(request)

    @abstractmethod
    def _remove_request(self, request):
        pass

    def close(self, request):
        self.remove(request)
        request.close()

    def execute(self):
        return self._curl.execute()

    def get_status(self):
        status = self._get_requests_status()

        return _check_status_codes(status)

    def _get_requests_status(self):
        handles_remaining, curl_completed, curl_failed = self._curl.info_read()

        request_completed = [self._get_request(curl) for curl in curl_completed]
        request_failed = [(self._get_request(curl), CurlError(errno, msg)) for curl, errno, msg in curl_failed]

        return MultiRequestsStatus(request_completed, request_failed, handles_remaining)

    def _get_request(self, handle):
        request = self._find_request(handle)

        if not request:
            raise MissingHandle(handle)

        assert request.handle == handle

        return request

    @abstractmethod
    def _find_request(self, handle):
        pass

    def select(self, timeout=1):
        self._curl.select(timeout)


class MultiRequests(MultiRequestsBase):
    def __init__(self):
        super(MultiRequests, self).__init__()
        self._requests = []

    def _add_request(self, request):
        self._requests.append(request)

    def _remove_request(self, request):
        self._requests.remove(request)

    def _find_request(self, handle):
        for request in self._requests:
            if request.curl == handle:
                return request


class MultiRequestsStatus(object):

    def __init__(self, completed, failed, handles_remaining):
        self.completed = completed
        self.failed = failed
        self.handles_remaining = handles_remaining


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
                completed.append(request)
            except BadHeader:
                pass
        failed.append((request, error))

    return MultiRequestsStatus(completed, failed, status.handles_remaining)