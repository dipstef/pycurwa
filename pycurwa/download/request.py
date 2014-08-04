from .response import CurlDownloadResponse, HttpDownloadHeaders
from ..request import CurlRequestBase, CurlHeadersRequest


class HttpDownloadBase(CurlRequestBase):

    def __init__(self, method, url, headers=None, data=None, cookies=None):
        super(HttpDownloadBase, self).__init__(method, url, headers, data, cookies)

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

    def __init__(self, url, file_path, cookies, bucket=None, resume=False):
        super(HttpDownloadRequest, self).__init__('GET', url, file_path, cookies=cookies)
        self._response = CurlDownloadResponse(self, file_path, resume, bucket)

        if resume:
            self._curl.set_resume(self.received)


class DownloadHeadersRequest(CurlHeadersRequest):

    def __init__(self, url, cookies=None, bucket=None):
        super(DownloadHeadersRequest, self).__init__(url, cookies, bucket)

    def head(self):
        self.execute()
        return HttpDownloadHeaders(self._response.headers)