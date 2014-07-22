from .chunk import Range
from ...curl import set_range
from ..request import HttpDownloadRequest
from ...error import BadHeader, RangeNotSatisfiable


class HttpDownloadRange(HttpDownloadRequest):

    def __init__(self, url, file_path, cookies, log, bytes_range, bucket=None, resume=False):
        self._range = bytes_range
        super(HttpDownloadRange, self).__init__(url, file_path, cookies, log, bucket, resume)

    def _handle_resume(self):
        if not self._is_range_completed():
            self._set_bytes_range(self.arrived)

    def _handle_not_resumed(self):
        super(HttpDownloadRange, self)._handle_not_resumed()
        self._set_bytes_range()

    def _set_bytes_range(self, arrived=0):
        if not self._is_closed_range():
            bytes_range = '%i-' % (arrived + self._range.start)
        else:
            bytes_range = '%i-%i' % (self.downloaded, self._range.end + 1)

        set_range(self.curl, bytes_range)
        return bytes_range

    def _write_body(self, buf):
        if self._is_range_completed():
            return 0
        super(HttpDownloadRange, self)._write_body(buf)

    def _parse_header(self, buf):
        # as first chunk, we will parse the headers
        if self._range.start == 0:
            super(HttpDownloadRange, self)._parse_header(buf)

    def _is_range_completed(self):
        return self._is_closed_range() and self.arrived > self._range.size

    def stop(self):
        self._range = Range(0, 0)

    def _is_closed_range(self):
        return bool(self._range.end)

    @property
    def downloaded(self):
        return self._range.start + self.arrived

    def verify_header(self):
        try:
            return super(HttpDownloadRange, self).verify_header()
        except BadHeader, e:
            if e.code == 416:
                raise RangeNotSatisfiable(self.url, self.file_path, self._range)
            raise e


class HTTPChunk(HttpDownloadRange):

    def __init__(self, chunk, download):
        self.id = chunk.id

        super(HTTPChunk, self).__init__(download.url, chunk.path, download.cookies, download.log, chunk.range,
                                        download.bucket, chunk.resume)
        self._download = download
        self._chunk = chunk

    def __str__(self):
        if self._is_closed_range():
            return '<HTTPChunk id=%d, size=%d, arrived=%d>' % (self.id, self._range.size, self.arrived)
        return '<HTTPChunk id=%d, arrived=%d>' % (self.id, self.arrived)


class FirstChunk(HTTPChunk):
    def __init__(self, chunk, download):
        super(FirstChunk, self).__init__(chunk, download)

    def _set_bytes_range(self, arrived=0):
        pass

    def _parse_http_header(self):
        header = super(FirstChunk, self)._parse_http_header()
        self._set_header(header)
        return header

    def _parse_ftp_header(self, buf):
        header = super(FirstChunk, self)._parse_ftp_header(buf)
        self._set_header(header)
        return header

    def _set_header(self, header):
        self._download.disposition_name = header.file_name
        self._download.size = header.size