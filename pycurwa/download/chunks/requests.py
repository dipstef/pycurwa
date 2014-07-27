from collections import OrderedDict
from time import time

from . import ChunksDict
from .request import HttpChunk
from ...requests import MultiRequestsBase


class ChunkRequests(MultiRequestsBase):

    def __init__(self, chunks=()):
        self._chunks = ChunksDict()
        super(ChunkRequests, self).__init__(chunks)

    def _add(self, chunk):
        self._chunks[chunk.id] = chunk

    def _find_request(self, handle):
        return self._chunks.get(handle.chunk_id)

    def _remove(self, chunk):
        del self._chunks[chunk.id]

    @property
    def chunks(self):
        return list(self._chunks.values())

    def remove(self, chunk=None):
        if not chunk:
            for chunk in self:
                super(ChunkRequests, self).remove(chunk)
        else:
            super(ChunkRequests, self).remove(chunk)

    def close(self, chunk=None):
        if not chunk:
            for chunk in self:
                super(ChunkRequests, self).close(chunk)
        else:
            super(ChunkRequests, self).close(chunk)

    def __len__(self):
        return len(self._chunks)

    def __getitem__(self, item):
        return self._chunks[item]

    def __iter__(self):
        return iter(self._chunks.values())


class ChunkRequestsStatus(ChunkRequests):

    def __init__(self, chunks=()):
        super(ChunkRequestsStatus, self).__init__(chunks)

        self.ok = ChunksDict()
        self.failed = ChunksDict()
        self._downloads = ChunksDict(chunks)
        self.check = None
        self._last_finish = None

    def iterate_statuses(self):
        try:
            while not self._done():
                self.execute()

                self.check = time()
                status = self._get_finished_status()

                if not self._done():
                    if status:
                        self._update_chunks_status(status)

                        yield status

                    self.select(timeout=1)
        finally:
            self.close()

    def _get_finished_status(self):
        status = self.get_status()

        while status.handles_remaining:
            status = self.get_status()

        status = HttpChunksStatus(self._chunks, self.check, status)

        self._last_finish = status

        return status

    def _current_check_after_last(self, current_check, seconds=0.5):
        return self._last_finish or current_check - self._last_finish.check >= seconds


    @property
    def chunks_received(self):
        return OrderedDict(((chunk_id, chunk.received) for chunk_id, chunk in self._downloads.iteritems()))

    def _update_chunks_status(self, status):
        for chunk in self.ok.values():
            if chunk.id in status.failed:
                del self.ok[chunk.id]

        for chunk, error in self.failed.values():
            if chunk.id in status.ok:
                del self.failed[chunk.id]

        self.ok.update(status.ok)
        self.failed.update(status.failed)

        self._last_finish = self._current_status
        self._current_status = status

    def _done(self):
        return len(self.ok) >= len(self._chunks)


class ChunksDownloadsStatus(ChunkRequestsStatus):

    def __init__(self, chunks, cookies=None, bucket=None,refresh=0.5):
        downloads = [HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed()]
        super(ChunksDownloadsStatus, self).__init__(downloads)
        self.path = chunks.path
        self.size = chunks.size

        self._completed_size = sum((chunk.get_size() for chunk in chunks if chunk.is_completed()))
        self._current_status = None

        self._chunks_refresh_rate = refresh

    def _get_finished_status(self):
        if self._is_chunk_finish_refresh_time():
            return super(ChunksDownloadsStatus, self)._get_finished_status()

    def _is_chunk_finish_refresh_time(self):
        last_check = self._last_finish.check if self._last_finish else 0

        return self.check - last_check >= self._chunks_refresh_rate

    @property
    def received(self):
        return sum(self.chunks_received.values()) + self._completed_size

    def is_completed(self):
        return self.received >= self.size


class HttpChunksStatus(object):

    def __init__(self, chunks, check, status):
        self._chunks = chunks

        self.ok = ChunksDict(status.completed)
        self.failed = OrderedDict(((chunk.id, (chunk, error)) for chunk, error in status.failed))
        self.handles_remaining = status.handles_remaining

        self.check = check

    @property
    def last_error(self):
        return self.failed.values()[-1][1] if self.failed else None

    @property
    def chunks_received(self):
        return OrderedDict((chunk_id, chunk.received) for chunk_id, chunk in self._chunks.iteritems())

    @property
    def chunks_speed(self):
        return OrderedDict((chunk_id, chunk.get_speed()) for chunk_id, chunk in self._chunks.iteritems())