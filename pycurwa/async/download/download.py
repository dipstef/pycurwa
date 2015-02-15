from abc import abstractmethod

from httpy.client import cookie_jar
from httpy.error import HttpError

from .requests import AsyncFuture, AsyncRequest
from ..request import AsyncGet
from ...download import HttpDownloadRequests, ChunksDownloads
from ...download.request import HeadersRequest


class AsyncDownloadRequests(HttpDownloadRequests):

    def __init__(self, requests, cookies=cookie_jar, max_speed=None, timeout=30):
        super(AsyncDownloadRequests, self).__init__(cookies, max_speed, timeout)
        self._requests = requests

    def execute(self, request, path=None, chunks=1, resume=False, **kwargs):
        if request.method.lower() == 'head':
            return self._head(request, **kwargs)
        else:
            return super(AsyncDownloadRequests, self).execute(request, path, chunks, resume, **kwargs)

    def _head(self, request, **kwargs):
        request = AsyncFuture(self._requests, request, self._cookies)
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


class AsyncHead(AsyncRequest):
    def __init__(self, requests, request, on_completion, on_err, cookies):
        super(AsyncHead, self).__init__(requests, HeadersRequest(request), on_completion, on_err, cookies)


class AsyncHeadFuture(AsyncFuture):
    def __init__(self, requests, request, cookies=None):
        super(AsyncHeadFuture, self).__init__(requests, HeadersRequest(request), cookies)


class AsyncChunksDownloads(ChunksDownloads):

    def __init__(self, requests, request, cookies=None, bucket=None, max_attempts=5):
        super(AsyncChunksDownloads, self).__init__(request, cookies, bucket, max_attempts)
        self._requests = requests

        self._create_chunks()

    def _create_chunks(self):
        try:
            super(AsyncChunksDownloads, self)._create_chunks()
            self._submit()
        except BaseException, error:
            self._download_failed(error)

    def _resolve_download(self):
        outcome = AsyncGet()
        self._async_head(outcome.completed, outcome.failed)
        return outcome.get()

    def _async_head(self, completed, failed):
        AsyncHead(self._requests, self._request, completed, failed, cookies=self._cookies)

    def _submit(self):
        self._requests.add(self)

    def update(self, status):
        try:
            return super(AsyncChunksDownloads, self).update(status)
        except HttpError, e:
            self._download_failed(e)

    def _done_downloading(self, status):
        super(AsyncChunksDownloads, self)._done_downloading(status)
        self._download_completed(status)

    @abstractmethod
    def _download_failed(self, error):
        raise NotImplementedError

    @abstractmethod
    def _download_completed(self, status):
        raise NotImplementedError

    def close(self):
        self._requests.close(self)