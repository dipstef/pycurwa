from collections import OrderedDict

from ..chunks.request import HttpChunk
from ..chunks.error import FailedChunks
from ...error import DownloadedContentMismatch
from pycurwa.download.files.chunks import ChunksDict
from .req import MultiRequests, MultiRequestRefresh, MultiRequestsStatus


class ChunkRequests(object):

    def __init__(self, chunks, curl=None):
        self._requests = MultiRequests(chunks, curl)
        self.curl = self._requests._curl
        self._chunks = ChunksDict(chunks)

    def remove(self, chunk=None):
        if not chunk:
            self._requests.remove_all()
        else:
            self._requests.remove(chunk)

    def close(self, chunk=None):
        if not chunk:
            self._requests.close_all()
        else:
            self._requests.close(chunk)

    @property
    def chunks(self):
        return list(self._chunks.values())

    @property
    def chunks_received(self):
        return OrderedDict(((chunk_id, chunk.received) for chunk_id, chunk in self._chunks.iteritems()))

    def get_status(self):
        status = self._requests.get_status()
        if status:
            return HttpChunksStatus(self._chunks, status)

    def __getitem__(self, item):
        return self._chunks[item]


class HttpChunksStatus(MultiRequestsStatus):

    def __init__(self, chunks, status):
        self._chunks = chunks

        completed = ChunksDict(status.completed)
        failed = ChunksDict(status.failed)

        super(HttpChunksStatus, self).__init__(completed, failed, status.remaining, status.check)

    @property
    def chunks_received(self):
        return OrderedDict((chunk_id, chunk.received) for chunk_id, chunk in self._chunks.iteritems())

    @property
    def chunks_speed(self):
        return OrderedDict((chunk_id, chunk.get_speed()) for chunk_id, chunk in self._chunks.iteritems())


class ChunksStatuses(ChunkRequests):

    def __init__(self, chunks, curl=None):
        super(ChunksStatuses, self).__init__(chunks, curl)

        self.completed = ChunksDict()
        self.failed = ChunksDict()

    def get_status(self):
        status = super(ChunksStatuses, self).get_status()
        if status:
            self._update_chunks(status)
            return status

    def _update_chunks(self, status):
        self._update_chunks_status(status)

        if status.failed:
            raise FailedChunks(status)
        for chunk in status.completed.values():
            if not chunk.is_completed():
                raise DownloadedContentMismatch(chunk.path, chunk.received, chunk.size)

    def _update_chunks_status(self, status):
        for chunk in self.completed.values():
            if chunk.id in status.failed:
                del self.completed[chunk.id]

        for chunk in self.failed.values():
            if chunk.id in status.completed:
                del self.failed[chunk.id]

        self.completed.update(status.completed)
        self.failed.update(status.failed)

    def done(self):
        return len(self.completed) >= len(self._requests)


class ChunksRefresh(MultiRequestRefresh):

    def __init__(self, requests, refresh=0.5, stats=None):
        super(ChunksRefresh, self).__init__(requests.curl, refresh)
        self._requests = requests

        self._stats = stats

    def _get_status_refresh(self, now):
        status = super(ChunksRefresh, self)._get_status_refresh(now)

        if self._stats:
            self._stats.update_progress(now)

        return status

    def _status(self):
        return self._requests.get_status()

    def _done(self):
        return self._requests.done()

    def _close(self):
        self._requests.close()


class ChunksDownloads(ChunksStatuses):

    def __init__(self, chunks, cookies=None, bucket=None):
        downloads = [HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed()]
        super(ChunksDownloads, self).__init__(downloads)
        self.path = chunks.path
        self.size = chunks.size

        self._completed_size = sum((chunk.get_size() for chunk in chunks if chunk.is_completed()))

    @property
    def received(self):
        return sum(self.chunks_received.values()) + self._completed_size

    def is_completed(self):
        return self.received >= self.size
