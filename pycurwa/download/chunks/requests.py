from Queue import Queue
from collections import OrderedDict

from . import ChunksDict
from threading import Thread
from .request import HttpChunk
from .error import FailedChunks
from ...error import DownloadedContentMismatch
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

    def is_done(self):
        return self.is_completed()

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


class MultiRefreshChunks(MultiRequestRefresh):

    def __init__(self, downloads, refresh=0.5, stats=None):
        super(MultiRefreshChunks, self).__init__(curl=None, refresh=refresh)
        self._downloads = downloads
        self._register(downloads)
        self._stats = stats

    def _update_status(self, now):
        status = super(MultiRefreshChunks, self)._update_status(now)

        if self._stats:
            self._stats.update_progress(now)

        return status

    def _done(self):
        return self._downloads.is_done()


class ChunksRefresh(object):

    def __init__(self, downloads, refresh=0.5, stats=None):
        self._downloads = downloads
        self._refresh = MultiRefreshChunks(downloads, refresh, stats)

    def __iter__(self):
        t = Thread(target=self._refresh.perform)

        t.start()
        try:
            for status in self._downloads.iterate_updates():
                yield status
        finally:
            t.join()


class ChunksDownloads(ChunksDownloadsBase):

    def __init__(self, chunks, cookies=None, bucket=None):
        super(ChunksDownloads, self).__init__(chunks, cookies, bucket)
        self._queue = Queue()

    def _update(self, status):
        self._queue.put(status)

    def perform(self):
        for _ in self.iterate_updates():
            pass

    def iterate_updates(self):
        while not self.is_done():
            status = self._queue.get()
            super(ChunksDownloads, self)._update(status)
            yield status

        for chunk in self.chunks:
            chunk.close()