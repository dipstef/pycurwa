from pycurwa.download.response import CurlRangeDownload
from ..request import HttpDownloadBase


class HttpDownloadRange(HttpDownloadBase):

    def __init__(self, url, file_path, cookies, bytes_range, bucket=None, resume=False):
        super(HttpDownloadRange, self).__init__('GET', url, cookies=cookies)
        self._response = CurlRangeDownload(self, file_path, bytes_range, resume, bucket)


class HttpChunk(HttpDownloadRange):

    def __init__(self, url, chunk, cookies=None, bucket=None):
        super(HttpChunk, self).__init__(url, chunk.path, cookies, chunk.range, bucket, chunk.resume)
        self._header_parse = False

        self.id = chunk.id
        self._chunk = chunk


    @property
    def size(self):
        return self._chunk.size

    def is_completed(self):
        return self.size == self.received

    def __str__(self):
        if self._response.is_closed_range():
            return '<HTTPChunk id=%d, size=%d, arrived=%d>' % (self.id, self._response.range.size, self.received)
        else:
            return '<HTTPChunk id=%d, arrived=%d>' % (self.id, self.received)