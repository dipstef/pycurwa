from Queue import Queue
from threading import Thread, Event, Lock

from . import HttpDownloadBase
from .requests import HttpDownloadsRequests
from .chunks import HttpChunksRequest, ChunksFileDownload
from .chunks.requests import RequestsChunkDownloads
from ..requests import MultiRequestRefresh


class MultiDownloadsRequests(HttpDownloadsRequests):

    def __init__(self, bucket=None):
        self._requests = DownloadRefresh()
        super(MultiDownloadsRequests, self).__init__(MultiChunks(self._requests, bucket))
        self._request_thread = Thread(target=self._requests.perform)
        self._request_thread.start()

    def close(self):
        self._requests.close()
        self._request_thread.join()


class MultiDownloads(HttpDownloadBase):
    def __init__(self, bucket=None):
        super(MultiDownloads, self).__init__(MultiDownloadsRequests(bucket))


class DownloadRefresh(MultiRequestRefresh):

    def __init__(self, refresh=0.5):
        super(DownloadRefresh, self).__init__(refresh)
        self._closed = Event()
        self._lock = Lock()

    def add(self, requests):
        with self._lock:
            super(DownloadRefresh, self).add(requests)

    def _update(self):
        with self._lock:
            return super(DownloadRefresh, self)._update()

    def remove(self, requests):
        with self._lock:
            super(DownloadRefresh, self).remove(requests)

    def _done(self):
        return self._closed.is_set()

    def close(self):
        return self._closed.set()


class MultiChunks(HttpChunksRequest):

    def __init__(self, requests, bucket=None):
        super(MultiChunks, self).__init__(ChunksThreadDownload(requests, bucket=bucket))


class ChunksThreadDownload(ChunksFileDownload):

    def __init__(self, requests, cookies=None, bucket=None):
        super(ChunksThreadDownload, self).__init__(cookies, bucket)
        self._requests = requests

    def _get_chunks(self, chunks_file):
        return RequestsChunks(self._requests, chunks_file, self._cookies, self._bucket)


class RequestsChunks(RequestsChunkDownloads):

    def __init__(self, requests, chunks, cookies=None, bucket=None):
        super(RequestsChunks, self).__init__(requests, chunks, cookies, bucket)
        self._queue = Queue()

    def _update(self, status):
        self._queue.put(status)

    def _get_status(self):
        status = self._queue.get()
        return status