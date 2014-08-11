from httpy.client import cookie_jar

from .. import PyCurwa
from .request import CurlRequestFuture, AsyncRequest
from .requests import Requests, RequestsProcess, RequestsUpdates, RequestsStatuses


class PyCurwaAsync(PyCurwa):

    def __init__(self, max_connections=20, cookies=cookie_jar, bucket=None, timeout=30):
        super(PyCurwaAsync, self).__init__(cookies, bucket, timeout)
        self._requests = Requests(max_connections)
        self._updates = CurlUpdates(self._requests)

    def execute(self, request, on_completion=None, on_err=None, **kwargs):
        request = AsyncRequest(request, on_completion, on_err, self._cookies, self._bucket)

        self._requests.add(request)
        return request

    def close(self):
        self._close()

    def _close(self):
        self._updates.stop()


class PyCurwaFutures(PyCurwaAsync):

    def execute(self, request, **kwargs):
        request = CurlRequestFuture(request, self._cookies, self._bucket)

        self._requests.add(request)
        return request.get_response()


class CurlUpdates(RequestsUpdates):

    def __init__(self, requests):
        super(CurlUpdates, self).__init__(requests)

    def _send_updates(self, status):
        for request in status.completed:
            request.completed()

        for request in status.failed:
            request.failed(request.error)