from Queue import Queue

from .requests import DownloadRequests
from .. import HttpDownloadBase, HttpDownloadRequests, HttpDownloadRequest
from ..chunks import HttpChunksDownload


class MultiDownloads(HttpDownloadBase):
    def __init__(self, bucket=None):
        super(MultiDownloads, self).__init__(MultiDownloadsRequests(bucket))

    def close(self):
        self._requests.close()


class MultiDownloadsRequests(HttpDownloadRequests):

    def __init__(self, bucket=None):
        self._requests = DownloadRequests()
        super(MultiDownloadsRequests, self).__init__(bucket)

    def _request(self, url, file_path, chunks_number, resume):
        return ChunksThreadRequest(self._requests, url, file_path, chunks_number, resume, self._bucket)

    def close(self):
        self._requests.close()


class ChunksThreadRequest(HttpDownloadRequest):

    def __init__(self, requests, url, file_path, chunks_number=1, resume=True, bucket=None):
        self._requests = requests
        super(ChunksThreadRequest, self).__init__(url, file_path, chunks_number, resume, bucket)

    def _create_request(self, chunks_file):
        return ChunksThreadDownload(self._requests, chunks_file, bucket=self._bucket)


class ChunksThreadDownload(HttpChunksDownload):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(ChunksThreadDownload, self).__init__(chunks_file, cookies, bucket)
        self._requests = requests
        self._queue = Queue()

    def _download_requests(self):
        return self._perform(self._requests)

    def _update(self, status):
        self._queue.put(status)

    def _get_status(self):
        status = self._queue.get()
        return status

    def close(self):
        self._requests.remove(self)
        super(ChunksThreadDownload, self).close()