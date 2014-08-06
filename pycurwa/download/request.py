from .response import CurlDownloadResponse, HttpDownloadHeaders, CurlRangeDownload
from ..request import CurlHeadersRequest, CurlRequest


class HttpDownloadBase(CurlRequest):

    def __init__(self, request, file_path, cookies=None, bucket=None, resume=False):
        self.path = file_path
        self.resume = resume

        super(HttpDownloadBase, self).__init__(request, cookies, bucket)

    def get_speed(self):
        return self._curl.get_speed_download()

    @property
    def received(self):
        return self._response.received

    @property
    def size(self):
        return self._response.size

    def _create_response(self):
        return CurlDownloadResponse(self, self._cookies, self._bucket)


class HttpDownloadRequest(HttpDownloadBase):

    def __init__(self, request, file_path, cookies=None, bucket=None, resume=False):
        super(HttpDownloadRequest, self).__init__(request, file_path, cookies, bucket, resume)

        if resume:
            self._curl.set_resume(self.received)


class DownloadHeadersRequest(CurlHeadersRequest):

    def __init__(self, url, headers=None, data=None, cookies=None):
        super(DownloadHeadersRequest, self).__init__(url, headers, data, cookies=cookies)

    def head(self):
        headers = super(DownloadHeadersRequest, self).head()
        return HttpDownloadHeaders(headers)


class HttpDownloadRange(HttpDownloadBase):

    def __init__(self, request, file_path, bytes_range, cookies=None, bucket=None, resume=False):
        self.range = bytes_range
        super(HttpDownloadRange, self).__init__(request, file_path, cookies, bucket, resume)

        self._curl.set_range(self.received + self.range.start, self.range.end)

    def _create_response(self):
        return CurlRangeDownload(self, self._cookies, self._bucket)