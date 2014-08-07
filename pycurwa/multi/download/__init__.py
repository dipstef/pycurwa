from Queue import Queue

from httpy.client import cookie_jar
from procol.console import print_err_trace
from .requests import DownloadRequests

from ...download import HttpDownloadRequests
from ...download.chunks import ChunksDownloads, HttpChunks


class MultiDownloadsRequests(HttpDownloadRequests):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        super(MultiDownloadsRequests, self).__init__(cookies, bucket, timeout)
        self._requests = DownloadRequests()

    def _create_request(self, chunks_file):
        return RequestsChunksDownload(self._requests, chunks_file, self._cookies, self._bucket)

    def close(self):
        self._requests.stop()


class MultiDownloads(MultiDownloadsRequests):

    def execute(self, request, path, chunks=1, resume=False):
        download = super(MultiDownloads, self).execute(request, path, chunks, resume)
        return download.perform()


class RequestsChunksDownload(ChunksDownloads):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(RequestsChunksDownload, self).__init__(requests, chunks_file, cookies, bucket)

    def perform(self):
        return self._chunks.perform()

    def _create_http_chunks(self, chunks_file):
        return ChunksCompletion(self._requests, chunks_file, self._cookies, self._bucket)


class ChunksMultiRequests(HttpChunks):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(ChunksMultiRequests, self).__init__(chunks_file, cookies, bucket)
        self._requests = requests
        #starts downloads right away
        self.submit()

    def submit(self):
        self._requests.add(self)

    def close(self):
        self._requests.close(self)


class ChunksCompletion(ChunksMultiRequests):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        self._outcome = Queue(1)
        super(ChunksCompletion, self).__init__(requests, chunks_file, cookies, bucket)

    def _update(self, status):
        try:
            return super(ChunksCompletion, self)._update(status)
        except BaseException, e:
            print_err_trace()
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