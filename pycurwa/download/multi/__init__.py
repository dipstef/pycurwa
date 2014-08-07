from Queue import Queue

from httpy.client import cookie_jar

from .requests import DownloadRequests
from ..requests import HttpDownloadRequest, HttpDownloadRequests
from ..chunks.download import HttpChunks


class MultiDownloadsRequests(HttpDownloadRequests):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        self._requests = DownloadRequests()
        super(MultiDownloadsRequests, self).__init__(cookies, bucket, timeout)

    def _get_request(self, request, path, chunks, resume):
        return ChunksThreadRequest(self._requests, request, path, chunks, resume, self._bucket)

    def close(self):
        self._requests.close()


class MultiDownloads(MultiDownloadsRequests):

    def execute(self, request, path, chunks=1, resume=False):
        download = super(MultiDownloads, self).execute(request, path, chunks, resume)
        return download.perform()

    def close(self):
        self._requests.close()


class ChunksThreadRequest(HttpDownloadRequest):

    def __init__(self, requests, request, path, chunks=1, resume=False, cookies=None, bucket=None):
        self._requests = requests
        super(ChunksThreadRequest, self).__init__(request, path, chunks, resume, cookies, bucket)

    def _create_request(self, chunks_file):
        return ChunksThreadDownload(self._requests, chunks_file, self._cookies, self._bucket)


class ChunksThreadDownload(HttpChunks):

    def __init__(self, request, chunks_file, cookies=None, bucket=None):
        super(ChunksThreadDownload, self).__init__(chunks_file, cookies, bucket)
        self._requests = requests
        self._outcome = Queue(1)

    def _download_requests(self):
        if self._chunks:
            self._requests.add(self)

            outcome = self._outcome.get()
            if isinstance(outcome, Exception):
                raise outcome

    def _update(self, status):
        try:
            return super(ChunksThreadDownload, self)._update(status)
        except BaseException, e:
            self._outcome.put(e)

    def _done_downloading(self, status):
        status = super(ChunksThreadDownload, self)._done_downloading(status)

        self._outcome.put(status)

    def close(self):
        self._requests.remove(self)
        super(ChunksThreadDownload, self).close()