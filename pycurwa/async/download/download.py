from httpy.client import cookie_jar

from ..request import CurlRequestFuture
from ...download import HttpDownloadRequests


class AsyncDownloadRequests(HttpDownloadRequests):

    def __init__(self, requests, cookies=cookie_jar, max_speed=None, timeout=30):
        super(AsyncDownloadRequests, self).__init__(cookies, max_speed, timeout)
        self._requests = requests

    def execute(self, request, path=None, chunks=1, resume=False, **kwargs):
        if request.method.lower() == 'head':
            return self._head(request, **kwargs)
        else:
            return super(AsyncDownloadRequests, self).execute(request, path=None, chunks=1, resume=False, **kwargs)

    def _head(self, request, **kwargs):
        request = AsyncHeadFuture(self._requests, request, self._cookies)
        return request.get_response()

    def close(self):
        self._close()

    def _close(self):
        self.stop()

    def stop(self, complete=False):
        self._requests.stop(complete)

    def pause(self):
        self._requests.pause()

    def resume(self):
        self._requests.resume()


class AsyncHead(object):

    def __init__(self, requests, request):
        self._request = request
        requests.add(self)

    def update(self, status):
        if status.completed:
            self._request.completed()
        elif status.failed:
            self._request.failed(status.failed[0].error)

    def __iter__(self):
        return iter([self])

    def __getattr__(self, item):
        return getattr(self._request, item)


class AsyncHeadFuture(AsyncHead):
    def __init__(self, requests, request, cookies=None):
        super(AsyncHeadFuture, self).__init__(requests, CurlRequestFuture(request, cookies))