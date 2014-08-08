from Queue import Queue

from httpy.client import cookie_jar
from procol.console import print_err_trace

from .requests import DownloadRequests

from ...download import HttpDownloadRequests
from ...download.chunks import ChunksDownloads


class MultiDownloadsRequests(HttpDownloadRequests):

    def __init__(self, cookies=cookie_jar, bucket=None, max_connections=10, timeout=30):
        super(MultiDownloadsRequests, self).__init__(cookies, bucket, timeout)
        self._requests = DownloadRequests(max_connections)

    def _create_request(self, chunks_file):
        return RequestsChunksDownload(self._requests, chunks_file, self._cookies, self._bucket)

    def close(self):
        self._requests.stop()


class MultiDownloads(MultiDownloadsRequests):

    def execute(self, request, path, chunks=1, resume=False):
        download = super(MultiDownloads, self).execute(request, path, chunks, resume)
        return download.perform()


class ChunksMultiRequests(ChunksDownloads):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(ChunksMultiRequests, self).__init__(requests, chunks_file, cookies, bucket)
        self._requests = requests
        #starts downloads right away
        self._submit()

    def _submit(self):
        self._requests.add(self)

    def close(self):
        self._requests.close(self)


class RequestsChunksDownload(ChunksMultiRequests):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        self._outcome = Queue(1)
        super(RequestsChunksDownload, self).__init__(requests, chunks_file, cookies, bucket)

    def _wait_termination(self):
        if self._chunks:
            outcome = self._outcome.get()
            if isinstance(outcome, Exception):
                raise outcome

    def _update(self, status):
        try:
            return super(RequestsChunksDownload, self)._update(status)
        except BaseException, e:
            print_err_trace()
            self._outcome.put(e)

    def _done_downloading(self, status):
        status = super(RequestsChunksDownload, self)._done_downloading(status)
        self._outcome.put(status)
