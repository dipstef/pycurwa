import os
from time import time

from procol.console import print_err

from . import ChunksDict
from .chunk import Range
from pycurwa.download.chunks.stats import DownloadStats
from .status import ChunksDownloadStatus
from ...curl import set_range, CurlMulti, PyCurlError
from ..request import HttpDownloadRequest
from ...error import BadHeader, RangeNotSatisfiable


class HttpDownloadRange(HttpDownloadRequest):

    def __init__(self, url, file_path, cookies, bytes_range, bucket=None, resume=False):
        self._range = bytes_range
        super(HttpDownloadRange, self).__init__(url, file_path, cookies, bucket, resume)

    def _handle_resume(self):
        if not self._is_range_completed():
            super(HttpDownloadRange, self)._handle_resume()
            self._set_bytes_range(self.received)

    def _handle_not_resumed(self):
        super(HttpDownloadRange, self)._handle_not_resumed()
        self._set_bytes_range()

    def _set_bytes_range(self, arrived=0):
        if not self._is_closed_range():
            bytes_range = '%i-' % (arrived + self._range.start)
        else:
            bytes_range = '%i-%i' % (self.range_downloaded, self._range.end + 1)

        set_range(self.curl, bytes_range)
        return bytes_range

    def _write_body(self, buf):
        if self._is_range_completed():
            return 0
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

    def __str__(self):
        if self._is_closed_range():
            return '<HTTPChunk id=%d, size=%d, arrived=%d>' % (self.id, self._range.size, self.received)
        else:
            return '<HTTPChunk id=%d, arrived=%d>' % (self.id, self.received)


class FirstChunk(HttpChunk):
    def __init__(self, url, chunk, cookies=None, bucket=None):
        super(FirstChunk, self).__init__(url, chunk, cookies, bucket)
        self._header_parse = True
        self.disposition_name = None
        self.size = 0

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
        self.disposition_name = header.file_name
        self.size = header.size


class HttpChunks(object):

    def __init__(self, chunks, cookies=None, bucket=None):
        self._chunks = ChunksDict((HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks))
        self.chunks_file = chunks
        self.curl = CurlMulti()

        for http_chunk in self._chunks.values():
            self.curl.add_handle(http_chunk.curl)

        self.url = chunks.url
        self.path = chunks.file_path
        self.size = chunks.size
        self._status = ChunksDownloadStatus(self._chunks)
        self._cookies = cookies
        self._bucket = bucket
        self.stats = DownloadStats(self.path, self.size)

    def close(self):
        for chunk in self:
            self._close_chunk(chunk)

    def is_completed(self):
        return self._status.received == self.chunks_file.size

    @property
    def chunks(self):
        return list(self._chunks.values())

    def _close_chunk(self, chunk):
        try:
            self.curl.remove_handle(chunk.curl)
        except PyCurlError, e:
            print_err('Error removing chunk: %s' % str(e))
        finally:
            chunk.close()

    def _remove_chunk(self, chunk):
        self._close_chunk(chunk)
        os.remove(chunk.path)

    def _update_status(self):
        status = self._status.check_finished(self.curl, seconds=0.5)

        for chunk, error in status.failed.values():
            print_err('Chunk %d failed: %s' % (chunk.id + 1, str(error)))

        self.stats.update_progress(status)

        return status

    def __len__(self):
        return len(self._chunks)

    def __getitem__(self, item):
        return self._chunks[item]

    def __iter__(self):
        return iter(self._chunks.values())