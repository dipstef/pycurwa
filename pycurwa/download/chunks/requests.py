from collections import OrderedDict

from .status import HttpChunksStatus, DownloadStats
from ..error import FailedChunks
from ..files import ChunksDict
from ...error import DownloadedContentMismatch, Abort


class ChunkRequests(object):

    def __init__(self, request, chunks):
        self._request = request
        self._chunks = ChunksDict(chunks)

        self._download_size = sum(chunk.size for chunk in chunks)
        self._completed_size = sum((chunk.get_size() for chunk in chunks if chunk.is_completed()))

    def update(self, status):
        status = HttpChunksStatus(status, self.chunks_received)
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
    def chunks_received(self):
        return OrderedDict(((chunk_id, chunk.received) for chunk_id, chunk in self._chunks.iteritems()))

    @property
    def received(self):
        return sum(self.chunks_received.values()) + self._completed_size

    @property
    def size(self):
        return self._download_size + self._completed_size

    def is_completed(self):
        return self.received >= self.size

    def __iter__(self):
        return self._chunks.itervalues()

    def __getitem__(self, item):
        return self._chunks[item]


class ChunksStatuses(ChunkRequests):

    def __init__(self, request, chunks):
        super(ChunksStatuses, self).__init__(request, chunks)

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

    def is_done(self):
        return len(self.completed) >= len(self._chunks) or bool(self.failed)


class ChunksDownload(ChunksStatuses):

    def __init__(self, request, downloads):
        super(ChunksDownload, self).__init__(request, downloads)
        self.stats = DownloadStats(request.path, self.size)
        self._abort = False

    def _update(self, status):
        if self._abort:
            raise Abort(self._request)

        super(ChunksDownload, self)._update(status)
        self.stats.update_progress(status)
