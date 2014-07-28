from ..request import HttpDownloadBase
from ...error import BadHeader, RangeNotSatisfiable


class HttpDownloadRange(HttpDownloadBase):

    def __init__(self, url, file_path, cookies, bytes_range, bucket=None, resume=False):
        self._range = bytes_range
        super(HttpDownloadRange, self).__init__(url, file_path, cookies, bucket, resume)

        start = self.received + self._range.start
        bytes_range = '%i-%i' % (start, self._range.end) if self._is_closed_range() else '%i-' % start

        self._curl.set_range(bytes_range)

    def _write_body(self, buf):
        if not self._is_range_completed():
            super(HttpDownloadRange, self)._write_body(buf)
        else:
            raise Exception('Above Range: ', self.path, self._range, self.received + len(buf))

    def _parse_header(self, buf):
        if self._header_parse:
            super(HttpDownloadRange, self)._parse_header(buf)

    def _is_range_completed(self):
        return self._is_closed_range() and self.received > self._range.size

    def _is_closed_range(self):
        return bool(self._range.end)

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


    @property
    def size(self):
        return self._chunk.size

    def __str__(self):
        if self._is_closed_range():
            return '<HTTPChunk id=%d, size=%d, arrived=%d>' % (self.id, self._range.size, self.received)
        else:
            return '<HTTPChunk id=%d, arrived=%d>' % (self.id, self.received)