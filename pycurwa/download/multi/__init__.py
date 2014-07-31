from Queue import Queue

from .requests import DownloadRequests

from .. import HttpDownloadBase, HttpDownloadRequests
from ..chunks import DownloadChunks
from ..chunks.requests import RequestsChunkDownloads


class MultiDownloadsRequests(HttpDownloadRequests):

    def __init__(self, bucket=None):
        self._requests = DownloadRequests()
        super(MultiDownloadsRequests, self).__init__(bucket)

    def _request(self, url, file_path, chunks_number, resume):
        return ChunksThreadDownload(self._requests, url, file_path, chunks_number, resume, self._bucket)

    def close(self):
        self._requests.close()


class MultiDownloads(HttpDownloadBase):
    def __init__(self, bucket=None):
        super(MultiDownloads, self).__init__(MultiDownloadsRequests(bucket))

    def close(self):
        self._requests.close()


class ChunksThreadDownload(DownloadChunks):

    def __init__(self, requests, url, path, chunks_number=1, resume=True, bucket=None):
        self._requests = requests
        super(ChunksThreadDownload, self).__init__(url, path, chunks_number, resume, bucket)

    def _get_chunks_download(self, chunks_file):
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