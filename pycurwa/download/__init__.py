import os
from httpy.client import cookie_jar

from .chunks import ChunksDownloads
from .request import ChunksDownloadRequest
from .. import PyCurwa
from ..curl.requests import RequestsRefresh


class HttpDownloadRequests(PyCurwa):

    def __init__(self, cookies=cookie_jar, max_speed=None, timeout=30):
        super(HttpDownloadRequests, self).__init__(cookies, timeout)
        self.set_speed(kbytes=max_speed)

    def get(self, url, path=None, chunks=1, resume=False, params=None, headers=None, **kwargs):
        return super(HttpDownloadRequests, self).get(url, params, headers, path=path, chunks=chunks, resume=resume,
                                                     **kwargs)

    def execute(self, request, path=None, chunks=1, resume=False, **kwargs):
        download = ChunksDownloadRequest(request, path or os.getcwd(), max(chunks, 1), resume)
        return self._create_download(download, **kwargs)

    def _head(self, request, **kwargs):
        return super(HttpDownloadRequests, self).execute(request, **kwargs)

    def _create_download(self, request, **kwargs):
        return DownloadChunks(request, cookies=self._cookies, bucket=self._bucket)


class HttpDownload(HttpDownloadRequests):

    def execute(self, request, path=None, chunks=1, resume=False, **kwargs):
        download = super(HttpDownload, self).execute(request, path, chunks, resume, **kwargs)
        return download.perform()


class DownloadChunks(ChunksDownloads):

    def __init__(self, request, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(request, cookies, bucket)
        self._requests = RequestsRefresh(refresh=0.5)

    def perform(self):
        self._request_chunks()
        self._submit()

        for status in self._requests.iterate_statuses():
            self.update(status)

        return self.stats

    def _submit(self):
        for request in self:
            self._requests.add(request)

    def close(self):
        for chunk in self._downloads:
            self._requests.close(chunk)