from collections import OrderedDict

from . import ChunksDict
from time import time
from .request import HttpChunk
from ...requests import MultiRequestsStatuses, MultiRequestsStatus


class ChunkRequests(MultiRequestsStatuses):

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
            for chunk in self._chunks.values():
                super(ChunkRequests, self).remove(chunk)
        else:
            super(ChunkRequests, self).remove(chunk)

    def close(self, chunk=None):
        if not chunk:
            self._close_all()
        else:
            super(ChunkRequests, self).close(chunk)

    @property
    def chunks(self):
        return list(self._request_handles.values())

    def __getitem__(self, item):
        return self._chunks[item]

    def get_status(self):
        status = super(ChunkRequests, self).get_status()
        return HttpChunksStatus(self._chunks, status)


class ChunkRequestsStatus(ChunkRequests):

    def __init__(self, chunks=()):
        super(ChunkRequestsStatus, self).__init__(chunks)

        self.completed = ChunksDict()
        self.failed = ChunksDict()
        self._downloads = ChunksDict(chunks)

    def iterate_statuses(self):
        for status in super(ChunkRequests, self).iterate_statuses():
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

        self._last_status = self._current_status
        self._current_status = status

    @property
    def chunks_received(self):
        return OrderedDict(((chunk_id, chunk.received) for chunk_id, chunk in self._downloads.iteritems()))

    def _done(self):
        return len(self.completed) >= len(self._chunks)


class ChunksDownloads(ChunkRequestsStatus):

    def __init__(self, chunks, cookies=None, bucket=None,refresh=0.5):
        downloads = [HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed()]
        super(ChunksDownloads, self).__init__(downloads)
        self.path = chunks.path
        self.size = chunks.size

        self._completed_size = sum((chunk.get_size() for chunk in chunks if chunk.is_completed()))
        self._current_status = None

        self._chunks_refresh_rate = refresh

    def get_status(self):
        if self._is_chunk_finish_refresh_time():
            return super(ChunksDownloads, self).get_status()
        return self._last_status

    def _is_chunk_finish_refresh_time(self):
        last_check = self._last_status.check if self._last_status else 0

        return time() - last_check >= self._chunks_refresh_rate

    @property
    def received(self):
        return sum(self.chunks_received.values()) + self._completed_size

    def is_completed(self):
        return self.received >= self.size


class HttpChunksStatus(MultiRequestsStatus):

    def __init__(self, chunks, status):
        self._chunks = chunks

        completed = ChunksDict(status.completed)
        failed = ChunksDict(status.failed)

        super(HttpChunksStatus, self).__init__(status.check, completed, failed, status.handles_remaining)

    @property
    def last_error(self):
        return self.failed.values()[-1].error if self.failed else None

    @property
    def chunks_received(self):
        return OrderedDict((chunk_id, chunk.received) for chunk_id, chunk in self._chunks.iteritems())

    @property
    def chunks_speed(self):
        return OrderedDict((chunk_id, chunk.get_speed()) for chunk_id, chunk in self._chunks.iteritems())