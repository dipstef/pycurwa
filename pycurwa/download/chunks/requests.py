from collections import OrderedDict

from . import ChunksDict
from time import time
from pycurwa.error import FailedChunks, DownloadedContentMismatch
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

    def get_status(self):
        status = super(ChunkRequests, self).get_status()
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

    def _iterate_statuses(self):
        for status in super(ChunksStatuses, self)._iterate_statuses():
            self._update_chunks_status(status)

            if status.failed:
                raise FailedChunks(status)

            for chunk in status.completed.values():
                if not chunk.is_completed():
                    raise DownloadedContentMismatch(chunk.path, chunk.received, chunk.size)

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


class ChunksRefresh(ChunksStatuses):

    def __init__(self, chunks_requests, refresh=0.5):
        super(ChunksRefresh, self).__init__(chunks_requests)
        self._chunks_refresh_rate = refresh
        self._last_status = None

    def _iterate_statuses(self):
        for status in super(ChunksStatuses, self)._iterate_statuses():
            if status:
                self._update_chunks_status(status)
                yield status
                self._last_status = status

    def _get_status(self):
        if self._is_chunk_finish_refresh_time():
            return super(ChunksRefresh, self)._get_status()

    def _is_chunk_finish_refresh_time(self):
        return time() - self._last_update >= self._chunks_refresh_rate

    @property
    def _last_update(self):
        return self._last_status.check if self._last_status else 0


class ChunksDownloads(ChunkRequests):

    def __init__(self, chunks, cookies=None, bucket=None):
        downloads = [HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed()]
        super(ChunksDownloads, self).__init__(downloads)
        self.path = chunks.path
        self.size = chunks.size

        self._downloads = ChunksDict(downloads)

        self._completed_size = sum((chunk.get_size() for chunk in chunks if chunk.is_completed()))
        self._statuses = ChunksStatuses(self)

    @property
    def chunks_received(self):
        return OrderedDict(((chunk_id, chunk.received) for chunk_id, chunk in self._downloads.iteritems()))

    @property
    def received(self):
        return sum(self.chunks_received.values()) + self._completed_size

    def is_completed(self):
        return self.received >= self.size