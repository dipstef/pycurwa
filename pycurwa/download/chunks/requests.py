from collections import OrderedDict

from . import ChunksDict
from time import time
from .request import HttpChunk
from ...requests import MultiRequests, MultiRequestsStatuses, MultiRequestsStatus


class ChunkRequests(MultiRequests):

    def __init__(self, chunks=()):
        self._chunks = ChunksDict()
        super(ChunkRequests, self).__init__(chunks)

    def _add(self, request):
        super(ChunkRequests, self)._add(request)
        self._chunks[request.id] = request

    def _remove(self, request):
        super(ChunkRequests, self)._remove(request)
        del self._chunks[request.id]

    def remove(self, chunk=None):
        if not chunk:
            self.remove_all()
        else:
            super(ChunkRequests, self).remove(chunk)

    def close(self, chunk=None):
        if not chunk:
            self.close_all()
        else:
            super(ChunkRequests, self).close(chunk)

    @property
    def chunks(self):
        return list(self._request_handles.values())

    def __getitem__(self, item):
        return self._chunks[item]

    def get_status(self, status_time=None):
        status = super(ChunkRequests, self).get_status(status_time)
        return HttpChunksStatus(self._chunks, status)


class HttpChunksStatus(MultiRequestsStatus):

    def __init__(self, chunks, status):
        self._chunks = chunks

        completed = ChunksDict(status.completed)
        failed = ChunksDict(status.failed)

        super(HttpChunksStatus, self).__init__(completed, failed, status.handles_remaining, status.check)

    @property
    def chunks_received(self):
        return OrderedDict((chunk_id, chunk.received) for chunk_id, chunk in self._chunks.iteritems())

    @property
    def chunks_speed(self):
        return OrderedDict((chunk_id, chunk.get_speed()) for chunk_id, chunk in self._chunks.iteritems())


class ChunksStatuses(MultiRequestsStatuses):

    def __init__(self, chunks_requests):
        super(ChunksStatuses, self).__init__(chunks_requests)

        self.completed = ChunksDict()
        self.failed = ChunksDict()

    def iterate_statuses(self):
        for status in super(ChunksStatuses, self).iterate_statuses():
            self._update_chunks_status(status)
            yield status

    def _update_chunks_status(self, status):
        for chunk in self.completed.values():
            if chunk.id in status.failed:
                del self.completed[chunk.id]

        for chunk in self.failed.values():
            if chunk.id in status.completed:
                del self.failed[chunk.id]

        self.completed.update(status.completed)
        self.failed.update(status.failed)

    def _done(self):
        return len(self.completed) >= len(self._requests)


class ChunksPeriodicalRefresh(ChunkRequests):

    def __init__(self, chunks=(), refresh=0.5):
        super(ChunksPeriodicalRefresh, self).__init__(chunks)
        self._last_check = None
        self._last_status = None
        self._chunks_refresh_rate = refresh

    def get_status(self, status_time=None):
        if self._is_chunk_finish_refresh_time():
            self._last_check = time()

            return super(ChunksPeriodicalRefresh, self).get_status(self._last_check)

        return self._last_status

    def _is_chunk_finish_refresh_time(self):
        last_check = self._last_status.check if self._last_status else 0

        return time() - last_check >= self._chunks_refresh_rate


class ChunksDownloads(ChunksPeriodicalRefresh):

    def __init__(self, chunks, cookies=None, bucket=None, refresh=0.5):
        downloads = [HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed()]

        super(ChunksDownloads, self).__init__(downloads, refresh)
        self.path = chunks.path
        self.size = chunks.size

        self._downloads = ChunksDict(downloads)

        self._completed_size = sum((chunk.get_size() for chunk in chunks if chunk.is_completed()))
        self._statuses = ChunksStatuses(self)

    def iterate_statuses(self):
        return self._statuses.iterate_statuses()

    @property
    def chunks_received(self):
        return OrderedDict(((chunk_id, chunk.received) for chunk_id, chunk in self._downloads.iteritems()))

    @property
    def received(self):
        return sum(self.chunks_received.values()) + self._completed_size

    def is_completed(self):
        return self.received >= self.size
