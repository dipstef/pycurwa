import os

from httpy import HttpHeaders
from httpy.http.headers.content import disposition_file_name, content_length

from .files.util import fs_encode
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

    __headers_class__ = HttpDownloadHeaders

    def __init__(self, request, file_path, resume=False, bucket=None):
        self.path = fs_encode(file_path)

        self._fp = open(file_path, 'ab' if resume else 'wb')

        super(CurlDownloadResponse, self).__init__(request, self._fp.write, bucket)

        if resume:
            self.received = self._fp.tell() or os.stat(self.path).st_size

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
    def __init__(self, request, file_path, bytes_range, resume=False, bucket=None):
        super(CurlRangeDownload, self).__init__(request, file_path, resume, bucket)
        self.range = bytes_range

        start = self.received + self.range.start

        self._curl.set_range('%i-%i' % (start, self.range.end) if self.is_closed_range() else '%i-' % start)

    def _write_body(self, buf):
        if not self._is_range_completed():
            super(CurlRangeDownload, self)._write_body(buf)
        else:
            raise Exception('Above Range: ', self.path, self.range, self.received + len(buf))

    def _is_range_completed(self):
        return self.is_closed_range() and self.received > self.range.size

    def is_closed_range(self):
        return bool(self.range.end)