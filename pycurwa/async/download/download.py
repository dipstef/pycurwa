from abc import abstractmethod
from httpy.client import cookie_jar
from httpy.error import HttpError
from pycurwa.async.request import AsyncCallback

from .requests import AsyncFuture, AsyncRequest
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

    def __init__(self, requests, request, chunks, cookies=None, bucket=None):
        super(AsyncChunksDownloads, self).__init__(request, chunks, cookies, bucket)
        self._requests = requests

        self._request_chunks()

    def _request_chunks(self):
        outcome = AsyncCallback(completed=self._create_chunks_file,
                                failed=lambda request, error: self._download_failed(error))
        self._request_head(outcome.completed, outcome.failed)
        outcome.wait()

    def _request_head(self, completed, failed):
        AsyncHead(self._requests, self._request, completed, failed, cookies=self._cookies)

    def _create_chunks_file(self, response):
        super(AsyncChunksDownloads, self)._create_chunks_file(response)
        #starts downloads right away
        self._submit()

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