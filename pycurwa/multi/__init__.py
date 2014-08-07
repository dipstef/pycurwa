from httpy.client import cookie_jar

from pycurwa import PyCurwa
from .request import CurlMultiRequest
from .requests import Requests, RequestsProcess, RequestsUpdates, RequestsStatuses


class PyCurwaMulti(PyCurwa):

    def __init__(self, max_connections=20, cookies=cookie_jar, bucket=None, timeout=30):
        super(PyCurwaMulti, self).__init__(cookies, bucket, timeout)
        self._requests = Requests(max_connections)
        self._updates = CurlUpdates(self._requests)

    def execute(self, request, **kwargs):
        request = CurlMultiRequest(request, self._cookies, self._bucket)

        self._requests.add(request)
        return request.get_response()

    def close(self):
        self._close()

    def _close(self):
        self._updates.stop()


class CurlUpdates(RequestsUpdates):

    def __init__(self, requests):
        super(CurlUpdates, self).__init__(requests)

    def _send_updates(self, status):
        for request in status.completed:
            request.update(status.check)

        for request in status.failed:
            request.update(request.error)