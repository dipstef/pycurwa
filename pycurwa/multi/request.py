from Queue import Queue
from threading import Event
from ..request import CurlRequestBase
from ..response import CurlBodyResponse


class CurlMultiRequest(CurlRequestBase):

    def __init__(self, request, cookies=None, bucket=None):
        super(CurlMultiRequest, self).__init__(request, cookies)
        self._outcome = Queue(1)
        self._response = CurlMultiResponse(self, self._outcome, cookies, bucket)

    def update(self, outcome):
        self._outcome.put(outcome)

    def close(self):
        self._response.close()

    def get_response(self):
        return self._response


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