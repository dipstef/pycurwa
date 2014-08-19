from abc import abstractmethod
from httpy.client import cookie_jar

from .. import PyCurwa
from .request import CurlRequestFuture, AsyncRequest
from .requests import Requests, RequestsProcess, RequestsUpdates, RequestsStatuses


class PyCurwaAsyncBase(PyCurwa):

    def __init__(self, max_connections=20, cookies=cookie_jar, timeout=30):
        super(PyCurwaAsyncBase, self).__init__(cookies, timeout)
        self._requests = CurlUpdates(max_connections)

    def execute(self, request,  **kwargs):
        request = self._create_request(request, **kwargs)

        self._requests.add(request)
        return request

    @abstractmethod
    def _create_request(self, request, **kwargs):
        raise not NotImplementedError

    def close(self):
        self._close()

    def _close(self):
        self._requests.stop()

    def pause(self, complete=False):
        self._requests.pause(complete)
        
    def resume(self):
        self._requests.resume()


class PyCurwaAsync(PyCurwaAsyncBase):

    def get(self, url, params=None, headers=None, on_completion=None, on_err=None, **kwargs):
        return super(PyCurwaAsync, self).get(url, params, headers, on_completion=on_completion, on_err=on_err, **kwargs)

    def _create_request(self, request, on_completion=None, on_err=None):
        return AsyncRequest(request, on_completion, on_err, self._cookies, self._bucket)

    def _close(self):
        self._requests.stop(complete=True)


class PyCurwaFutures(PyCurwaAsyncBase):

    def execute(self, request, **kwargs):
        request = super(PyCurwaFutures, self).execute(request, **kwargs)
        return request.get_response()

    def _create_request(self, request, **kwargs):
        return CurlRequestFuture(request, self._cookies, self._bucket)


class CurlUpdates(RequestsUpdates):

    def __init__(self, max_connections):
        super(CurlUpdates, self).__init__(Requests(max_connections))

    def _send_updates(self, status):
        for request in status.completed:
            request.completed()

        for request in status.failed:
            request.failed(request.error)