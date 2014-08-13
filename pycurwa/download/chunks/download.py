from .request import HttpChunk
from .requests import ChunksDownload
from ..error import ChunksDownloadMismatch


class HttpChunks(ChunksDownload):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        self._cookies = cookies
        self._bucket = bucket

        downloads = [self._chunk_request(chunks_file.request, chunk) for chunk in chunks_file.remaining()]
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
        except BaseException:
            self.close()
            raise

    def _done_downloading(self, status):
        self.close()
        self._verify_completed()
        self._chunks_file.copy_chunks()
        self._completed = True

    def _verify_completed(self):
        if not self.is_completed():
            raise ChunksDownloadMismatch(self._request, self)

    def _is_done(self):
        return len(self.completed) >= len(self._chunks) or bool(self.failed)

    def close(self):
        for chunk in self.chunks:
            chunk.close()

    def _chunk_request(self, request, chunk):
        return HttpChunk(request, chunk, self._cookies, self._bucket)