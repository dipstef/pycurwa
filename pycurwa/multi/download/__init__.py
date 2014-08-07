from Queue import Queue

from httpy.client import cookie_jar

from .requests import DownloadRequests
from ...download.chunks import HttpChunks, ChunksDownloads
from ...download.requests import HttpDownloadRequests, HttpDownloadRequest


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
        return RequestsChunksDownload(self._requests, chunks_file, self._cookies, self._bucket)


class RequestsChunksDownload(ChunksDownloads):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        self._requests = requests
        super(RequestsChunksDownload, self).__init__(chunks_file, cookies, bucket)

    def _create_http_chunks(self, chunks_file):
        chunks = ChunksCompletion(chunks_file, self._cookies, self._bucket)
        #will start downloading before the perform method has been invoked
        self._requests.add(chunks)
        return chunks


class ChunksCompletion(HttpChunks):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(ChunksCompletion, self).__init__(chunks_file, cookies, bucket)
        self._outcome = Queue(1)

    def _update(self, status):
        try:
            return super(ChunksCompletion, self)._update(status)
        except BaseException, e:
            self._outcome.put(e)

    def _done_downloading(self, status):
        status = super(ChunksCompletion, self)._done_downloading(status)

        self._outcome.put(status)

    def perform(self):
        if self._chunks:
            outcome = self._outcome.get()
            if isinstance(outcome, Exception):
                raise outcome

        return self.stats