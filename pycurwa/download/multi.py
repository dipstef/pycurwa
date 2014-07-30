from threading import Thread, Event, Lock

from . import HttpDownloadBase
from .chunks.download import DownloadChunks, HttpChunks
from pycurwa.download.chunks.requests import ChunksDownloads
from pycurwa.requests import MultiRequestRefresh


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


class MultiDownloads(HttpDownloadBase):

    def __init__(self, bucket=None):
        self._requests = DownloadRefresh()
        super(MultiDownloads, self).__init__(MultiChunks(bucket, self._requests))
        self._request_thread = Thread(target=self._requests.perform)
        self._request_thread.start()

    def close(self):
        self._requests.close()
        self._request_thread.join()


class MultiChunks(DownloadChunks):

    def __init__(self, bucket, requests):
        super(MultiChunks, self).__init__(bucket)
        self._requests = requests

    def _create_download(self, chunks_file):
        downloads = RequestsChunks(self._requests, chunks_file, bucket=self._bucket)

        return HttpChunks(downloads)


class RequestsChunks(ChunksDownloads):
    def __init__(self, requests, chunks, cookies=None, bucket=None):
        super(RequestsChunks, self).__init__(chunks, cookies, bucket)
        self._requests = requests
        self._requests.add(self)

    def close(self):
        self._requests.remove(self)
        super(RequestsChunks, self).close()
