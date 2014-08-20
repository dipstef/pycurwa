from Queue import Queue
from abc import abstractmethod
from threading import Event
from httpy.client import cookie_jar
from .requests import DownloadRequests, AsyncRequest
from .download import AsyncDownloadRequests, AsyncChunksDownloads, AsyncHead
from .group import DownloadGroups
from ..request import AsyncCallback, AsyncGet


class AsyncDownloadsBase(AsyncDownloadRequests):

    def __init__(self, cookies=cookie_jar, max_speed=None, max_connections=10, timeout=30):
        super(AsyncDownloadsBase, self).__init__(DownloadRequests(max_connections), cookies, max_speed, timeout)

    @abstractmethod
    def _create_download(self, request, **kwargs):
        raise NotImplementedError


class AsyncDownloads(AsyncDownloadsBase):

    def _head(self, request, on_completion=None, on_err=None, **kwargs):
        return AsyncRequest(self._requests, request, on_completion, on_err, self._cookies)

    def _create_download(self, request, on_completion=None, on_err=None, **kwargs):
        return AsyncChunks(self._requests, request, on_completion, on_err, self._cookies, self._bucket)

    def _close(self):
        self.stop(complete=True)


class AsyncChunks(AsyncChunksDownloads):

    def __init__(self, requests, request, on_completion=None, on_err=None, cookies=None, bucket=None):
        self._on_completion = on_completion
        self._on_err = on_err
        super(AsyncChunks, self).__init__(requests, request, cookies, bucket)

    def _download_failed(self, error):
        if self._on_err:
            self._on_err(self, error)

    def _download_completed(self, status):
        if self._on_completion:
            self._on_completion(self)


class AsyncDownloadFutures(AsyncDownloadsBase):

    def _create_download(self, request, **kwargs):
        return AsyncChunksFutures(self._requests, request, self._cookies, self._bucket)

    def group(self):
        return DownloadGroups(self._requests, self._cookies, self._bucket)

    def _close(self):
        self.stop()


class AsyncChunksFutures(AsyncChunks):

    def __init__(self, requests, request, cookies=None, bucket=None):
        self._outcome = AsyncGet()
        super(AsyncChunksFutures, self).__init__(requests, request, self._outcome.completed, self._outcome.failed,
                                                 cookies, bucket)

    def perform(self):
        if self._chunks:
            return self._outcome.get()

        return self.stats