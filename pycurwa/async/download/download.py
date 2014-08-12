from httpy.client import cookie_jar

from ..request import CurlRequestFuture
from ...download import HttpDownloadRequests


class AsyncDownloadRequests(HttpDownloadRequests):

    def __init__(self, requests, cookies=cookie_jar, bucket=None, timeout=30):
        super(AsyncDownloadRequests, self).__init__(cookies, bucket, timeout)
        self._requests = requests

    def _head(self, request, **kwargs):
        request = HeadRequestFuture(request, self._cookies)
        self._requests.add(request)
        return request.get_response()

    def close(self):
        self._close()

    def _close(self):
        self._requests.stop()


class HeadRequestFuture(CurlRequestFuture):

    def update(self, status):
        if status.completed:
            self.completed()
        elif status.failed:
            self.failed(status.failed[0].error)

    def __iter__(self):
        return iter([self])