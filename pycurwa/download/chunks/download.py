from .request import HttpChunk
from .requests import ChunksDownload
from ..error import ChunksDownloadMismatch


class HttpChunks(ChunksDownload):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        downloads = [HttpChunk(chunks_file.request, chunk, cookies, bucket) for chunk in chunks_file.remaining()]
        super(HttpChunks, self).__init__(chunks_file.request, downloads)

        self._chunks_file = chunks_file
        self._completed = False

        if not downloads and chunks_file.chunks:
            self._verify_completed()

    def update(self, status):
        try:
            super(HttpChunks, self).update(status)

            if self._is_done():
                self._done_downloading(status)
        except BaseException, e:
            self.close()
            raise

    def _done_downloading(self, status):
        try:
            self.close()
            self._verify_completed()
            self._completed = True
        except BaseException:
            raise

    def _verify_completed(self):
        if not self.is_completed():
            raise ChunksDownloadMismatch(self._request, self)

        self._chunks_file.copy_chunks()

    def _is_done(self):
        return len(self.completed) >= len(self._chunks) or bool(self.failed)

    def close(self):
        for chunk in self.chunks:
            chunk.close()


class HttpChunksRequests(HttpChunks):
    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(HttpChunksRequests, self).__init__(chunks_file, cookies, bucket)
        self._requests = requests

    def submit(self):
        for chunk in self.chunks:
            self._requests.add(chunk)

    def close(self):
        for chunk in self.chunks:
            self._requests.close(chunk)