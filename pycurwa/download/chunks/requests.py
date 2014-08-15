from .status import ChunksCompletion, HttpChunksStatus, DownloadStats
from ..request import DownloadRequest
from ..error import FailedChunks
from ..files import ChunksDict
from ...error import DownloadedContentMismatch


class ChunkRequests(DownloadRequest):

    def __init__(self, request):
        super(ChunkRequests, self).__init__(request, request.path, request.resume)
        self._request = request

    def _create_chunks(self, chunks):
        self._chunks = ChunksCompletion(chunks)

    def update(self, status):
        status = HttpChunksStatus(status, self._chunks.chunks_received)
        self._update(status)

    def _update(self, status):
        if status.failed:
            raise FailedChunks(self._request, status)

        for chunk in status.completed.values():
            if not chunk.is_completed():
                raise DownloadedContentMismatch(self._request, chunk.path, chunk.received, chunk.size)

    @property
    def chunks(self):
        return list(self._chunks.values())

    @property
    def size(self):
        return self._chunks.size

    def is_completed(self):
        return self._chunks.received >= self.size

    def __iter__(self):
        return self._chunks.itervalues()

    def __getitem__(self, item):
        return self._chunks[item]


class ChunksStatuses(ChunkRequests):

    def __init__(self, request):
        super(ChunksStatuses, self).__init__(request)

    def _create_chunks(self, chunks):
        super(ChunksStatuses, self)._create_chunks(chunks)
        self.completed = ChunksDict()
        self.failed = ChunksDict()

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

        self.completed.update(status.completed)
        self.failed.update(status.failed)


class ChunksDownload(ChunksStatuses):

    def __init__(self, request):
        super(ChunksDownload, self).__init__(request)

    def _create_chunks(self, chunks):
        super(ChunksDownload, self)._create_chunks(chunks)
        self.stats = DownloadStats(self.path, self.size)

    def _update(self, status):
        super(ChunksDownload, self)._update(status)
        self.stats.update_progress(status)

    @property
    def speed(self):
        return self.stats.speed