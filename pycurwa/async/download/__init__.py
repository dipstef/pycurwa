from Queue import Queue
from abc import abstractmethod
from threading import Event
from httpy.client import cookie_jar
from .requests import DownloadRequests, AsyncChunksDownloads
from .download import AsyncDownloadRequests, AsyncHead
from .group import DownloadGroups
from .. import AsyncRequest


class AsyncDownloadsBase(AsyncDownloadRequests):

    def __init__(self, cookies=cookie_jar, bucket=None, max_connections=10, timeout=30):
        super(AsyncDownloadsBase, self).__init__(DownloadRequests(max_connections), cookies, bucket, timeout)

    @abstractmethod
    def _create_download(self, request, chunks, **kwargs):
        raise NotImplementedError


class AsyncDownloads(AsyncDownloadsBase):

    def _head(self, request, on_completion=None, on_err=None, **kwargs):
        return AsyncHead(self._requests, AsyncRequest(request, on_completion, on_err, self._cookies))

    def _create_download(self, request, chunks, on_completion=None, on_err=None, **kwargs):
        return AsyncChunks(self._requests, request, chunks, on_completion, on_err, self._cookies, self._bucket)

    def _close(self):
        self._requests.stop(complete=True)


class AsyncChunks(AsyncChunksDownloads):

    def __init__(self, requests, request, chunks, on_completion=None, on_err=None, cookies=None, bucket=None):
        self._on_completion = on_completion
        self._on_err = on_err
        super(AsyncChunks, self).__init__(requests, request, chunks, cookies, bucket)

    def _download_failed(self, error):
        if self._on_err:
            self._on_err(self, error)

    def _download_completed(self, status):
        if self._on_completion:
            self._on_completion(self)


class AsyncDownloadFutures(AsyncDownloadsBase):

    def _create_download(self, request, chunks, **kwargs):
        return AsyncChunksFutures(self._requests, request, chunks, self._cookies, self._bucket)

    def group(self):
        return DownloadGroups(self._requests, self._cookies, self._bucket)


class AsyncChunksFutures(AsyncChunksDownloads):

    def __init__(self, requests, request, chunks, cookies=None, bucket=None):
        self._outcome = Queue(1)
        self._performed = Event()
        super(AsyncChunksFutures, self).__init__(requests, request, chunks, cookies, bucket)

    def perform(self):
        if self._chunks or self._performed.is_set():
            outcome = self._outcome.get()
            if isinstance(outcome, Exception):
                raise outcome

        return self.stats

    def _download_completed(self, status):
        self._performed.set()
        self._outcome.put(status.check)

    def _download_failed(self, error):
        self._performed.set()
        self._outcome.put(error)