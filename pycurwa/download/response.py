import os

from httpy import HttpHeaders
from httpy.http.headers.content import disposition_file_name, content_length

from .error import AboveRange
from ..response import CurlResponse


class HttpDownloadHeaders(HttpHeaders):

    @property
    def chunk_support(self):
        return 'bytes' == self.get('accept-ranges', '')

    @property
    def file_name(self):
        return disposition_file_name(self)

    @property
    def size(self):
        return content_length(self)


class CurlDownloadResponse(CurlResponse):

    __headers__ = HttpDownloadHeaders

    def __init__(self, request, cookies=None, bucket=None):
        self.path = request.path

        self._fp = open(self.path, 'ab' if request.resume else 'wb')

        super(CurlDownloadResponse, self).__init__(request, self._fp.write, cookies, bucket)

        if request.resume:
            self.received = self._fp.tell() or os.path.getsize(self.path)

    def close(self):
        self._flush()
        self._fp.close()

    def _flush(self):
        self._fp.flush()
        os.fsync(self._fp.fileno())

    @property
    def chunk_support(self):
        return self.headers.chunk_support

    @property
    def disposition_name(self):
        return self.headers.file_name

    @property
    def size(self):
        return self.headers.size


class CurlRangeDownload(CurlDownloadResponse):

    def __init__(self, request, cookies=None, bucket=None):
        super(CurlRangeDownload, self).__init__(request, cookies, bucket)
        self.range = request.range

    def _write_body(self, buf):
        if not self._is_range_completed():
            super(CurlRangeDownload, self)._write_body(buf)
        else:
            raise AboveRange(self.request, self.path, self.received + len(buf), self.range.size)

    def _is_range_completed(self):
        return self._is_closed_range() and self.received > self.range.size

    def _is_closed_range(self):
        return bool(self.range.end)