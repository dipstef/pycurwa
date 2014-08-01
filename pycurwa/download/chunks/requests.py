from collections import OrderedDict

from .status import HttpChunksStatus, DownloadStats
from .error import FailedChunks
from ..files import ChunksDict
from ...error import DownloadedContentMismatch, Abort
from ...requests import MultiRequestRefresh


class ChunkRequests(object):

    def __init__(self, chunks):
        self._chunks = ChunksDict(chunks)

        self._download_size = sum(chunk.size for chunk in chunks)
        self._completed_size = sum((chunk.get_size() for chunk in chunks if chunk.is_completed()))

    def update(self, status):
        self._update(HttpChunksStatus(status, self.chunks_received))

    def _update(self, status):
        if status.failed:
            raise FailedChunks(status)

        for chunk in status.completed.values():
            if not chunk.is_completed():
                raise DownloadedContentMismatch(chunk.path, chunk.received, chunk.size)

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

    def __init__(self, chunks):
        super(ChunksStatuses, self).__init__(chunks)

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
        return len(self.completed) >= len(self._chunks) or self.failed


class ChunksDownload(ChunksStatuses):

    def __init__(self, downloads):
        super(ChunksDownload, self).__init__(downloads)
        self.stats = DownloadStats(self.size)
        self._abort = False

    def perform(self):
        raise NotImplementedError

    def _perform(self, requests):
        requests.add(self)

        for _ in self._iterate_updates(requests):
            if self._abort:
                raise Abort()

        return self.stats

    def _get_status(self):
        raise NotImplementedError

    def _iterate_updates(self, requests):
        try:
            while not self.is_done():
                status = self._get_status()
                self._update_status(status)
                yield status
        finally:
            self.close()

    def _update_status(self, status):
        super(ChunksDownload, self)._update(status)
        self.stats.update_progress(status)

    def close(self):
        for chunk in self.chunks:
            chunk.close()


class MultiRefreshChunks(MultiRequestRefresh):

    def __init__(self, downloads, refresh=0.5):
        super(MultiRefreshChunks, self).__init__(refresh=refresh)
        self._downloads = downloads

    def _done(self):
        return self._downloads.is_done()