from Queue import Queue
from abc import abstractmethod
from httpy.client import cookie_jar

from .requests import DownloadRequests, AsyncChunksDownloads
from .download import AsyncDownloadRequests
from .group import DownloadGroups


class AsyncDownloadsBase(AsyncDownloadRequests):

    def __init__(self, cookies=cookie_jar, bucket=None, max_connections=10, timeout=30):
        super(AsyncDownloadsBase, self).__init__(DownloadRequests(max_connections), cookies, bucket, timeout)

    @abstractmethod
    def _create_request(self, chunks_file, **kwargs):
        raise NotImplementedError


class AsyncDownloads(AsyncDownloadsBase):

    def _create_request(self, chunks_file, on_completion=None, on_err=None, **kwargs):
        return AsyncChunks(self._requests, chunks_file, on_completion, on_err, self._cookies, self._bucket)

    def _close(self):
        self._requests.stop(complete=True)


class AsyncChunks(AsyncChunksDownloads):

    def __init__(self, requests, chunks_file, on_completion=None, on_err=None, cookies=None, bucket=None):
        self._on_completion = on_completion
        self._on_err = on_err
        super(AsyncChunks, self).__init__(requests, chunks_file, cookies, bucket)

    def _download_failed(self, error):
        if self._on_err:
            self._on_err(self, error)

    def _download_completed(self, status):
        if self._on_completion:
            self._on_completion(self)


class AsyncDownloadFutures(AsyncDownloadsBase):

    def _create_request(self, chunks_file, **kwargs):
        return AsyncChunksFutures(self._requests, chunks_file, self._cookies, self._bucket)

    def group(self):
        return DownloadGroups(self._requests, self._cookies, self._bucket)


class AsyncChunksFutures(AsyncChunksDownloads):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        self._outcome = Queue(1)
        super(AsyncChunksFutures, self).__init__(requests, chunks_file, cookies, bucket)

    def perform(self):
        if self._chunks:
            outcome = self._outcome.get()
            if isinstance(outcome, Exception):
                raise outcome

        return self.stats

    def _download_completed(self, status):
        self._outcome.put(status.check)

    def _download_failed(self, error):
        self._outcome.put(error)