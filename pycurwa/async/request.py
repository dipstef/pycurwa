from Queue import Queue
from abc import abstractmethod
from threading import Event

from ..request import CurlRequestBase
from ..response import CurlBodyResponse


class AsyncRequestBase(CurlRequestBase):

    def __init__(self, request, cookies=None, bucket=None):
        self._bucket = bucket
        super(AsyncRequestBase, self).__init__(request, cookies)

    @abstractmethod
    def completed(self):
        raise NotImplementedError

    @abstractmethod
    def failed(self, error):
        raise NotImplementedError

    def _create_response(self):
        return CurlBodyResponse(self, self._cookies, self._bucket)


class AsyncRequest(AsyncRequestBase):
    def __init__(self, request, on_completion, on_err, cookies=None, bucket=None):
        super(AsyncRequest, self).__init__(request, cookies, bucket)
        self._on_completion = on_completion
        self._on_err = on_err

    def completed(self):
        if self._on_completion:
            self._on_completion(self._response)

    def failed(self, error):
        if self._on_err:
            self._on_err(self, error)


class CurlRequestFuture(AsyncRequest):

    def __init__(self, request, cookies=None, bucket=None):
        self._outcome = Queue(1)
        super(CurlRequestFuture, self).__init__(request, cookies, bucket)

    def execute(self):
        assert self._response.status == 200
        return self._response

    def completed(self):
        self._outcome.put(self._response.date)

    def failed(self, error):
        self._outcome.put(error)

    def _create_response(self):
        return CurlResponseFuture(self, self._outcome, self._cookies, self._bucket)


class CurlResponseFuture(CurlBodyResponse):

    def __init__(self, request, outcome, cookies, bucket=None):
        super(CurlResponseFuture, self).__init__(request, cookies, bucket)
        self._outcome = outcome
        self._completed = Event()
        self._headers = None
        self._completion = None

    def read(self):
        self._wait_completed()

        return self._read()

    @property
    def headers(self):
        self._wait_completed()

        return self._headers

    @headers.setter
    def headers(self, value):
        self._headers = value

    @property
    def status(self):
        self._wait_completed()
        return super(CurlResponseFuture, self).status

    @property
    def url(self):
        self._wait_completed()
        return super(CurlResponseFuture, self).url

    def _wait_completed(self):
        if not self._completed.is_set():
            try:
                self._completion = self._outcome.get()
                self._completed.set()

            finally:
                self.close()

        if isinstance(self._completion, BaseException):
            raise self._completion