from ..request import HttpDownloadRange
from ..response import CurlRangeDownload


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
        size = '' if not self._chunk.range.end else ' size=%d, ' % self.range.size
        return '<%s id=%d,%s arrived=%d>' % (self.__class__.__name__, self.id, size, self._response.received)


class HttpChunkDownload(CurlRangeDownload):
    #avoids parsing headers
    __headers__ = None