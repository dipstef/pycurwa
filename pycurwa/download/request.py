from httpy.client import HttpyRequest
from .response import CurlDownloadResponse, CurlRangeDownload
from ..request import CurlRequest


class HttpDownloadBase(CurlRequest):

    def __init__(self, request, file_path, cookies=None, bucket=None, resume=False):
        self.path = file_path
        self.resume = resume

        super(HttpDownloadBase, self).__init__(request, cookies, bucket)

    @property
    def received(self):
        return self._response.received

    @property
    def size(self):
        return self._response.size

    def _create_response(self):
        return CurlDownloadResponse(self._curl, self, self._cookies, self._bucket)


class HttpDownloadRequest(HttpDownloadBase):

    def __init__(self, request, file_path, cookies=None, bucket=None, resume=False):
        super(HttpDownloadRequest, self).__init__(request, file_path, cookies, bucket, resume)

        if resume:
            self._curl.set_resume(self.received)


class HttpDownloadRange(HttpDownloadBase):

    def __init__(self, request, file_path, bytes_range, cookies=None, bucket=None, resume=False):
        self.range = bytes_range
        super(HttpDownloadRange, self).__init__(request, file_path, cookies, bucket, resume)

        start = self.received + self.range.start
        if start or self.range.end:
            self._curl.set_range(start, self.range.end)

    def _create_response(self):
        return CurlRangeDownload(self._curl, self, self._cookies, self._bucket)


class DownloadRequest(HttpyRequest):

    def __init__(self, request, path, resume=False):
        super(DownloadRequest, self).__init__(request.method, request.url, request.headers, request.data,
                                              request.params, request.timeout, request.redirect)
        self.path = path
        self.resume = resume


class ChunksDownloadRequest(DownloadRequest):

    def __init__(self, request, path, chunks=1, resume=False):
        super(ChunksDownloadRequest, self).__init__(request, path, resume)
        self.chunks_requested = chunks


class HeadersRequest(HttpyRequest):
    def __init__(self, request):
        super(HeadersRequest, self).__init__('HEAD', request.url, request.headers, request.data, request.params,
                                                  request.timeout, request.redirect)