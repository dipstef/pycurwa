from pycurwa.download.response import CurlRangeDownload
from ..request import HttpDownloadRange


class HttpChunk(HttpDownloadRange):

    def __init__(self, request, chunk, cookies=None, bucket=None):
        super(HttpChunk, self).__init__(request, chunk.path, chunk.download_range, cookies, bucket, chunk.resume)

        self._chunk = chunk

    @property
    def id(self):
        return self._chunk.id

    @property
    def size(self):
        return self._chunk.size

    def is_completed(self):
        return self.size == self.received

    def _create_response(self):
        return HttpChunkDownload(self, self._cookies, self._bucket)

    def __str__(self):
        if self.range.end:
            return '<HTTPChunk id=%d, size=%d, arrived=%d>' % (self.id, self.range.size, self._response.received)
        else:
            return '<HTTPChunk id=%d, arrived=%d>' % (self.id, self._response.received)


class HttpChunkDownload(CurlRangeDownload):
    #avoids parsing headers
    __headers__ = None