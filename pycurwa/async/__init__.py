from abc import abstractmethod
from httpy.client import cookie_jar

from .. import PyCurwa
from .request import CurlRequestFuture, AsyncRequest
from .requests import Requests, RequestsProcess, RequestsUpdates, RequestsStatuses


class PyCurwaAsyncBase(PyCurwa):

    def __init__(self, max_connections=20, cookies=cookie_jar, bucket=None, timeout=30):
        super(PyCurwaAsyncBase, self).__init__(cookies, bucket, timeout)
        self._requests = Requests(max_connections)
        self._updates = CurlUpdates(self._requests)

    def execute(self, request,  **kwargs):
        request = self._create_request(request)

        self._requests.add(request)
        return request

    @abstractmethod
    def _create_request(self, request, **kwargs):
        raise not NotImplementedError

    def close(self):
        self._close()

    def _close(self):
        self._updates.stop()


class PyCurwaAsync(PyCurwaAsyncBase):

    def _create_request(self, request, on_completion=None, on_err=None):
        return AsyncRequest(request, on_completion, on_err, self._cookies, self._bucket)


class PyCurwaFutures(PyCurwaAsyncBase):

    def execute(self, request, **kwargs):
        request = super(PyCurwaFutures, self).execute(request, **kwargs)
        return request.get_response()

    def _create_request(self, request, **kwargs):
        return CurlRequestFuture(request, self._cookies, self._bucket)


class CurlUpdates(RequestsUpdates):

    def __init__(self, requests):
        super(CurlUpdates, self).__init__(requests)

    def _send_updates(self, status):
        for request in status.completed:
            request.completed()

        for request in status.failed:
            request.failed(request.error)