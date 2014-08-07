from .request import HttpChunk
from .requests import ChunksDownload
from ..error import ChunksDownloadMismatch


class HttpChunks(ChunksDownload):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        downloads = [HttpChunk(chunks_file.request, chunk, cookies, bucket) for chunk in chunks_file.remaining()]
        super(HttpChunks, self).__init__(chunks_file.request, downloads)

        self._chunks_file = chunks_file
        if not downloads and chunks_file.chunks:
            self._verify_completed()

    def _update(self, status):
        super(HttpChunks, self)._update(status)

        if self.is_done():
            self._done_downloading(status)

    def _done_downloading(self, status):
        self._verify_completed()

        return status

    def _verify_completed(self):
        if not self.is_completed():
            raise ChunksDownloadMismatch(self._request, self)

        self._chunks_file.copy_chunks()