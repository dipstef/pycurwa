import os

from httpy.client import HttpyRequest
from httpy.http.headers.content import content_length, disposition_file_name

from .chunks import ChunksDownloads
from .files.download import get_chunks_file
from .files.util import save_join
from .. import PyCurwa
from ..curl.requests import RequestsRefresh


class HttpDownloadRequests(PyCurwa):

    def execute(self, request, path, chunks=1, resume=False):
        head_response = self.head(request.url, request.params, request.headers, request.data)

        if os.path.isdir(path):
            path = save_join(path, self._get_file_name(head_response))

        chunks = get_chunks_file(DownloadRequest(request, path, chunks, resume), self._content_length(head_response))
        return self._create_request(chunks)

    def _get_file_name(self, header_response):
        return self._content_disposition(header_response.headers) or self._url_file_name(header_response.url)

    def _content_disposition(self, headers):
        return disposition_file_name(headers)

    def _url_file_name(self, url):
        return os.path.basename(url)

    def _content_length(self, header_response):
        return content_length(header_response.headers)

    def _create_request(self, chunks_file):
        return DownloadChunks(chunks_file, cookies=self._cookies, bucket=self._bucket)


class DownloadRequest(HttpyRequest):

    def __init__(self, request, path, chunks=1, resume=False):
        super(DownloadRequest, self).__init__(request.method, request.url, request.headers, request.data,
                                              request.params, request.timeout, request.redirect)
        self.path = path
        self.chunks = max(chunks, 1)
        self.resume = resume


class HttpDownload(HttpDownloadRequests):

    def execute(self, request, path, chunks=1, resume=False):
        download = super(HttpDownload, self).execute(request, path, chunks, resume)
        return download.perform()


class DownloadChunks(ChunksDownloads):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(chunks_file, cookies, bucket)
        self._requests = RequestsRefresh(refresh=0.5)

    def perform(self):
        self._submit()

        for status in self._requests.iterate_statuses():
            for chunk in status.completed:
                self._requests.close(chunk)

            self.update(status)

        return self.stats

    def _submit(self):
        for request in self:
            self._requests.add(request)

    def close(self):
        for chunk in self.chunks:
            self._requests.close(chunk)