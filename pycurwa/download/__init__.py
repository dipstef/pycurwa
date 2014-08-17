import os

from .chunks import ChunksDownloads
from .request import DownloadRequest
from .. import PyCurwa
from ..curl.requests import RequestsRefresh


class HttpDownloadRequests(PyCurwa):

    def get(self, url, path=None, chunks=1, resume=False, params=None, headers=None, **kwargs):
        return super(HttpDownloadRequests, self).get(url, params, headers, path=path, chunks=chunks, resume=resume,
                                                     **kwargs)

    def execute(self, request, path=None, chunks=1, resume=False, **kwargs):
        path = path or os.getcwd()
        return self._create_download(DownloadRequest(request, path, resume), max(chunks, 1), **kwargs)

    def _head(self, request, **kwargs):
        return super(HttpDownloadRequests, self).execute(request, **kwargs)

    def _create_download(self, request, chunks, **kwargs):
        return DownloadChunks(request, chunks, cookies=self._cookies, bucket=self._bucket)


class HttpDownload(HttpDownloadRequests):

    def execute(self, request, path, chunks=1, resume=False):
        download = super(HttpDownload, self).execute(request, path, chunks, resume)
        return download.perform()


class DownloadChunks(ChunksDownloads):

    def __init__(self, request, chunks, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(request, cookies, bucket)
        self._requests = RequestsRefresh(refresh=0.5)
        self._chunks_number = chunks

    def perform(self):
        self._request_chunks(self._chunks_number)
        self._submit()

        for status in self._requests.iterate_statuses():
            self.update(status)

        return self.stats

    def _submit(self):
        for request in self:
            self._requests.add(request)

    def close(self):
        for chunk in self.chunks:
            self._requests.close(chunk)