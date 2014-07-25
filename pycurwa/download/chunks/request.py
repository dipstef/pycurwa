from .chunk import Range
from ..request import HttpDownloadRequest
from ...error import BadHeader, RangeNotSatisfiable


class HttpDownloadRange(HttpDownloadRequest):

    def __init__(self, url, file_path, cookies, bytes_range, bucket=None, resume=False):
        self._range = bytes_range
        super(HttpDownloadRange, self).__init__(url, file_path, cookies, bucket, resume)

    def _handle_resume(self):
        super(HttpDownloadRange, self)._handle_resume()
        if not self._is_range_completed():
            self._set_bytes_range(self.received)

    def _handle_not_resumed(self):
        super(HttpDownloadRange, self)._handle_not_resumed()
        self._set_bytes_range()

    def _set_bytes_range(self, arrived=0):
        if not self._is_closed_range():
            bytes_range = '%i-' % (arrived + self._range.start)
        else:
            bytes_range = '%i-%i' % (self.range_downloaded, self._range.end + 1)

        self._curl.set_range(bytes_range)
        return bytes_range

    def _write_body(self, buf):
        if not self._is_range_completed():
            super(HttpDownloadRange, self)._write_body(buf)

    def _parse_header(self, buf):
        if self._header_parse:
            super(HttpDownloadRange, self)._parse_header(buf)

    def _is_range_completed(self):
        return self._is_closed_range() and self.received > self._range.size

    def stop(self):
        self._range = Range(0, 0)

    def _is_closed_range(self):
        return bool(self._range.end)

    @property
    def range_downloaded(self):
        return self._range.start + self.received

    def verify_header(self):
        try:
            return super(HttpDownloadRange, self).verify_header()
        except BadHeader, e:
            if e.code == 416:
                raise RangeNotSatisfiable(self.url, self.path, self._range)
            raise e


class HttpChunk(HttpDownloadRange):

    def __init__(self, url, chunk, cookies=None, bucket=None):
        super(HttpChunk, self).__init__(url, chunk.path, cookies, chunk.range, bucket, chunk.resume)
        self._header_parse = False
        self.id = chunk.id
        self._chunk = chunk
        self.handle.chunk_id = chunk.id

    def __str__(self):
        if self._is_closed_range():
            return '<HTTPChunk id=%d, size=%d, arrived=%d>' % (self.id, self._range.size, self.received)
        else:
            return '<HTTPChunk id=%d, arrived=%d>' % (self.id, self.received)