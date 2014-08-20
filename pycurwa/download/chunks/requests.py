from .status import ChunksCompletion, DownloadStats, ChunksProgress
from ..request import ChunksDownloadRequest
from ..error import FailedChunks
from ...error import DownloadedContentMismatch


class ChunkRequests(ChunksDownloadRequest):

    def __init__(self, request):
        super(ChunkRequests, self).__init__(request, request.path, request.chunks_requested, request.resume)
        self._chunks = ChunksCompletion()

    def _add_chunks(self, chunks):
        self._chunks = ChunksCompletion(chunks)

    def update(self, status):
        self._chunks.update_progress(status)

        if status.failed:
            raise FailedChunks(self._request, status)

        for chunk in status.completed:
            if not chunk.is_completed():
                raise DownloadedContentMismatch(self._request, chunk.path, chunk.received, chunk.size)

    @property
    def _downloads(self):
        return list(self._chunks.remaining)

    @property
    def size(self):
        return self._chunks.size

    @property
    def _request(self):
        return ChunksDownloadRequest(self, self.path, self.chunks_requested, self.resume)

    def __iter__(self):
        return iter(self._chunks.remaining)


class ChunksDownload(ChunkRequests):

    def __init__(self, request):
        super(ChunksDownload, self).__init__(request)

    def _add_chunks(self, chunks):
        self._chunks = ChunksProgress(chunks)

    @property
    def speed(self):
        return self._chunks.speed

    @property
    def stats(self):
        return DownloadStats(self.path, self.size, self._chunks.speed)