from pycurwa.download.response import CurlRangeDownload
from .response import CurlDownloadResponse, HttpDownloadHeaders
from ..request import CurlRequestBase, CurlHeadersRequest


class HttpDownloadBase(CurlRequestBase):
    __response__ = CurlDownloadResponse

    def __init__(self, request, file_path, cookies=None, bucket=None, resume=False):
        super(HttpDownloadBase, self).__init__(request, cookies)
        self._response = self.__response__(self, file_path, resume, bucket)

    def get_speed(self):
        return self._curl.get_speed_download()

    def close(self):
        self._response.close()
        super(HttpDownloadBase, self).close()

    @property
    def received(self):
        return self._response.received

    @property
    def size(self):
        return self._response.size


class HttpDownloadRequest(HttpDownloadBase):

    def __init__(self, request, file_path, cookies=None, bucket=None, resume=False):
        super(HttpDownloadRequest, self).__init__(request, file_path, cookies, bucket, resume)

        if resume:
            self._curl.set_resume(self.received)


class DownloadHeadersRequest(CurlHeadersRequest):

    def __init__(self, url, cookies=None, bucket=None):
        super(DownloadHeadersRequest, self).__init__(url, cookies, bucket)

    def head(self):
        self._curl.perform()
        return HttpDownloadHeaders(self._response.headers)


class HttpDownloadRange(HttpDownloadBase):

    __response__ = CurlRangeDownload

    def __init__(self, request, file_path, bytes_range, cookies=None, bucket=None, resume=False):
        self.range = bytes_range
        super(HttpDownloadRange, self).__init__(request, file_path, cookies, bucket, resume)

        start = self.received + self.range.start

        self._curl.set_range('%i-%i' % (start, self.range.end) if self.is_closed_range() else '%i-' % start)

    def is_closed_range(self):
        return bool(self.range.end)