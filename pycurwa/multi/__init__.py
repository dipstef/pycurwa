from Queue import Queue
from threading import Event

from httpy.client import cookie_jar

from pycurwa import PyCurwa
from pycurwa.multi.requests import LimitedRequests, RequestsProcess, RequestsUpdates, RequestsStatuses
from pycurwa.request import CurlRequestBase
from pycurwa.response import CurlBodyResponse


class PyCurwaMulti(PyCurwa):

    def __init__(self, max_connections=20, cookies=cookie_jar, bucket=None, timeout=30):
        super(PyCurwaMulti, self).__init__(cookies, bucket, timeout)
        self._requests = LimitedRequests(max_connections)
        self._updates = CurlUpdates(self._requests)

    def execute(self, request, **kwargs):
        request = CurlMultiRequest(request, self._cookies, self._bucket)

        self._requests.add(request)
        return request.response

    def close(self):
        self._close()

    def _close(self):
        self._updates.stop()


class CurlUpdates(RequestsUpdates):

    def __init__(self, requests):
        super(CurlUpdates, self).__init__(requests)

    def _send_updates(self, status):
        for request in status.completed:
            self._requests.close(request)
            request.update(status.check)

        for request in status.failed:
            self._requests.close(request)
            request.update(request.error)

    def _is_status_update(self, status):
        return status.completed or status.failed


class CurlMultiRequest(CurlRequestBase):

    def __init__(self, request, cookies=None, bucket=None):
        super(CurlMultiRequest, self).__init__(request, cookies)
        self._outcome = Queue(1)
        self.response = CurlMultiResponse(self, self._outcome, cookies, bucket)

    def update(self, outcome):
        self._outcome.put(outcome)

    def close(self):
        self.response.close()


class CurlMultiResponse(CurlBodyResponse):

    def __init__(self, request, outcome, cookies, bucket=None):
        super(CurlMultiResponse, self).__init__(request, cookies, bucket)
        self._outcome = outcome
        self._completed = Event()
        self._headers = None

    def read(self):
        self._wait_completed()
        return self._read()

    def get_status_code(self):
        self._wait_completed()
        return super(CurlMultiResponse, self).get_status_code()

    @property
    def headers(self):
        self._wait_completed()
        return self._headers

    @headers.setter
    def headers(self, value):
        self._headers = value

    def _wait_completed(self):
        if not self._completed.is_set():
            outcome = self._outcome.get()
            self._completed.set()

            if isinstance(outcome, BaseException):
                raise outcome