from collections import OrderedDict

from .stats import DownloadStats
from .request import HttpChunk
from .error import FailedChunks
from ..files import ChunksDict
from ...error import DownloadedContentMismatch, Abort
from ...requests import MultiRequestRefresh, RequestsStatus


class ChunkRequests(object):

    def __init__(self, chunks):
        self._chunks = ChunksDict(chunks)

        self._download_size = sum(chunk.size for chunk in chunks)
        self._completed_size = sum((chunk.get_size() for chunk in chunks if chunk.is_completed()))

    def update(self, status):
        self._update(HttpChunksStatus(self._chunks, status))

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


class HttpChunksStatus(RequestsStatus):

    def __init__(self, chunks, status):
        self._chunks = chunks

        completed = ChunksDict(status.completed)
        failed = ChunksDict(status.failed)

        super(HttpChunksStatus, self).__init__(completed, failed, status.check)


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


class ChunksDownloadsBase(ChunksStatuses):

    def __init__(self, chunks, cookies=None, bucket=None):
        downloads = [HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed()]
        super(ChunksDownloadsBase, self).__init__(downloads)
        self.path = chunks.path
        self._abort = False

    def perform(self):
        stats = DownloadStats(self)
        for status in self._iterate_updates():
            if self._abort:
                raise Abort()
            stats.update_progress(status.check)
        return stats

    def _get_status(self):
        raise NotImplementedError

    def _iterate_updates(self):
        try:
            while not self.is_done():
                status = self._get_status()
                super(ChunksDownloadsBase, self)._update(status)
                yield status
        finally:
            self.close()

    def close(self):
        for chunk in self.chunks:
            chunk.close()


class RequestsChunkDownloads(ChunksDownloadsBase):

    def __init__(self, requests, chunks, cookies=None, bucket=None):
        super(RequestsChunkDownloads, self).__init__(chunks, cookies, bucket)
        self._requests = requests
        self._requests.add(self)

    def close(self):
        self._requests.remove(self)
        super(RequestsChunkDownloads, self).close()


class ChunksDownload(RequestsChunkDownloads):

    def __init__(self, chunks, cookies=None, bucket=None, refresh=0.5):
        super(ChunksDownload, self).__init__(MultiRefreshChunks(self, refresh), chunks, cookies, bucket)

    def _iterate_updates(self):
        return self._requests.iterate_updates()


class MultiRefreshChunks(MultiRequestRefresh):

    def __init__(self, downloads, refresh=0.5):
        super(MultiRefreshChunks, self).__init__(refresh=refresh)
        self._downloads = downloads

    def get_status(self):
        self._curl.execute()
        status = HttpChunksStatus(self._downloads, self._requests.get_status())

        self._curl.select(timeout=1)
        return status

    def _done(self):
        return self._downloads.is_done()