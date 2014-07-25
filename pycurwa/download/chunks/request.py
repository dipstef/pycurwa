import os

from . import ChunksDict
from .chunk import Range
from pycurwa.download.chunks.stats import DownloadStats
from pycurwa.request import MultiRequestsBase
from .status import ChunksDownloadStatus
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

        self.curl.set_range(bytes_range)
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
        self.curl.chunk_id = chunk.id

    def __str__(self):
        if self._is_closed_range():
            return '<HTTPChunk id=%d, size=%d, arrived=%d>' % (self.id, self._range.size, self.received)
        else:
            return '<HTTPChunk id=%d, arrived=%d>' % (self.id, self.received)


class FirstChunk(HttpChunk):
    def __init__(self, url, chunk, cookies=None, bucket=None):
        super(FirstChunk, self).__init__(url, chunk, cookies, bucket)
        self._header_parse = True

    def _set_bytes_range(self, arrived=0):
        pass


class ChunkRequests(MultiRequestsBase):

    def __init__(self, chunks=()):
        super(ChunkRequests, self).__init__()
        self._chunks = ChunksDict()
        for chunk in chunks:
            self.add(chunk)

    def _add_request(self, chunk):
        self._chunks[chunk.id] = chunk

    def _find_request(self, handle):
        return self._chunks.get(handle.chunk_id)

    def _remove_request(self, chunk):
        del self._chunks[chunk.id]

    @property
    def chunks(self):
        return list(self._chunks.values())

    def close(self, chunk=None):
        if not chunk:
            for chunk in self:
                self.close(chunk)
        else:
            super(ChunkRequests, self).close(chunk)

    def __len__(self):
        return len(self._chunks)

    def __getitem__(self, item):
        return self._chunks[item]

    def __iter__(self):
        return iter(self._chunks.values())


class HttpChunks(ChunkRequests):

    __slots__ = ('perform', )

    def __init__(self, chunks_file, cookies=None, bucket=None):
        chunks = (HttpChunk(chunks_file.url, chunk, cookies, bucket) for chunk in chunks_file)
        super(HttpChunks, self).__init__(chunks)

        self.chunks_file = chunks_file

        self.url = chunks_file.url
        self.path = chunks_file.file_path
        self.size = chunks_file.size
        self._status = ChunksDownloadStatus(self._chunks)
        self._cookies = cookies
        self._bucket = bucket
        self.stats = DownloadStats(self.path, self.size)

    def is_completed(self):
        #assert self._status.received == self.chunks_file.size
        return os.path.getsize(self.path) == self.chunks_file.size

    def _remove_chunk(self, chunk):
        self.close(chunk)
        os.remove(chunk.path)

    def _get_status(self):
        status = self._status.check_finished(self, seconds=0.5)

        self.stats.update_progress(status)

        return status