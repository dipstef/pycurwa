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
        self._outcome = AsyncGet()
        super(CurlRequestFuture, self).__init__(request, self._outcome.completed, self._outcome.failed, cookies, bucket)

    def execute(self):
        return self._outcome.get()

    def _create_response(self):
        return CurlResponseFuture(self, self._outcome, self._cookies, self._bucket)


class CurlResponseFuture(CurlBodyResponse):

    def __init__(self, request, outcome, cookies, bucket=None):
        super(CurlResponseFuture, self).__init__(request, cookies, bucket)
        self._outcome = outcome
        self._completed = Event()
        self._completion = None

    def read(self):
        self._wait_completed()

        return self._read()

    @property
    def headers(self):
        self._wait_completed()
        return self._headers

    @property
    def status(self):
        self._wait_completed()
        return super(CurlResponseFuture, self).status

    @property
    def url(self):
        self._wait_completed()
        return super(CurlResponseFuture, self).url

    def _wait_completed(self):
        try:
            self._outcome.get()
        finally:
            if not self._closed.is_set():
                self.close()


class AsyncCallback(object):

    def __init__(self, completed, failed):
        self._processed = Event()
        self._completed = completed
        self._failed = failed

    def completed(self, response):
        self._completed(response)
        self._processed.set()

    def failed(self, request, error):
        self._failed(request, error)
        self._processed.set()

    def wait(self):
        self._processed.wait()


class AsyncGet(object):
    def __init__(self):
        self._processed = Event()
        self._response = None
        self._error = None

    def completed(self, response):
        self._response = response
        self._processed.set()

    def failed(self, request, error):
        self._error = error
        self._processed.set()

    def get(self):
        self._processed.wait()
        if not self._response:
            raise self._error
        return self._response