from Queue import Queue

from httpy.client import cookie_jar
from procol.console import print_err_trace

from .requests import DownloadRequests, ChunksMultiRequests
from ...download import HttpDownloadRequests
from .group import GroupRequests


class MultiDownloadsRequests(HttpDownloadRequests):

    def __init__(self, cookies=cookie_jar, bucket=None, max_connections=10, timeout=30):
        super(MultiDownloadsRequests, self).__init__(cookies, bucket, timeout)
        self._requests = DownloadRequests(max_connections)

    def _create_request(self, chunks_file):
        return RequestsChunksDownload(self._requests, chunks_file, self._cookies, self._bucket)

    def create_group(self):
        return GroupRequests(self._requests, self._cookies, self._bucket)

    def close(self):
        self._close()

    def _close(self):
        self._requests.stop()


class RequestsChunksDownload(ChunksMultiRequests):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        self._outcome = Queue(1)
        super(RequestsChunksDownload, self).__init__(requests, chunks_file, cookies, bucket)
        #starts downloads right away
        self._submit()

    def perform(self):
        if self._chunks:
            outcome = self._outcome.get()
            if isinstance(outcome, Exception):
                raise outcome

        return self.stats

    def _update(self, status):
        try:
            return super(RequestsChunksDownload, self)._update(status)
        except BaseException, e:
            print_err_trace()
            self._outcome.put(e)

    def _done_downloading(self, status):
        status = super(RequestsChunksDownload, self)._done_downloading(status)
        self._outcome.put(status)
