from .status import ChunksCompletion, ChunksProgress, DownloadStats
from ..request import DownloadRequest
from ..error import FailedChunks
from ..files import ChunksDict
from ...error import DownloadedContentMismatch


class ChunkRequests(DownloadRequest):

    def __init__(self, request):
        super(ChunkRequests, self).__init__(request, request.path, request.resume)
        self._request = request
        self._chunks = ChunksCompletion()

    def _create_chunks(self, chunks):
        self._chunks = ChunksCompletion(chunks)

    def update(self, status):
        self._update(status)

    def _update(self, status):
        if status.failed:
            raise FailedChunks(self._request, status)

        for chunk in status.completed:
            if not chunk.is_completed():
                raise DownloadedContentMismatch(self._request, chunk.path, chunk.received, chunk.size)

    @property
    def chunks(self):
        return list(self._chunks.remaining)

    @property
    def size(self):
        return self._chunks.size

    def __iter__(self):
        return iter(self._chunks.remaining)


class ChunksStatuses(ChunkRequests):

    def __init__(self, request):
        super(ChunksStatuses, self).__init__(request)

    def _create_chunks(self, chunks):
        self._create_chunks_stats(chunks)
        self.completed = ChunksDict()
        self.failed = ChunksDict()

    def _create_chunks_stats(self, chunks):
        super(ChunksStatuses, self)._create_chunks(chunks)

    def _update(self, status):
        self._update_chunks_status(status)
        super(ChunksStatuses, self)._update(status)

    def _update_chunks_status(self, status):
        for chunk in self.completed.values():
            if chunk.id in status.failed:
                del self.completed[chunk.id]

        for chunk in self.failed.values():
            if chunk.id in status.completed:
                del self.failed[chunk.id]

        self.completed.update(ChunksDict(status.completed))
        self.failed.update(ChunksDict(status.failed))


class ChunksDownload(ChunksStatuses):

    def __init__(self, request):
        super(ChunksDownload, self).__init__(request)

    def _create_chunks_stats(self, chunks):
        self._chunks = ChunksProgress(chunks)

    def _update(self, status):
        super(ChunksDownload, self)._update(status)
        self._chunks.update_progress(status)

    @property
    def speed(self):
        return self._chunks.speed

    @property
    def stats(self):
        return DownloadStats(self.path, self.size, self._chunks.speed)