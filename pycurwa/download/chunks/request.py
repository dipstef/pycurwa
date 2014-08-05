from httpy import HttpRequest
from ..request import HttpDownloadRange


class HttpChunk(HttpDownloadRange):

    def __init__(self, request, chunk, cookies=None, bucket=None):
        super(HttpChunk, self).__init__(request, chunk.path, chunk.range, cookies, bucket, chunk.resume)
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