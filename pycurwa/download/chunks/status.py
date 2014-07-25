from collections import namedtuple, OrderedDict
from time import time

from pycurwa.download.chunks import ChunksDict


class FailedChunk(namedtuple('FailedChunk', ('chunk', 'error'))):

    @property
    def id(self):
        return self.chunk.id


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


class ChunksUnchanged(object):

    def __init__(self, chunks, check):
        super(ChunksUnchanged, self).__init__()
        self.chunks = chunks
        self.check = check
        self.failed = {}
        self.chunks_received = OrderedDict(((chunk_id, chunk.received) for chunk_id, chunk in chunks.iteritems()))


class ChunksDownloadStatus(object):

    def __init__(self, chunks):
        self._last_finish = None
        self._current_status = None

        self.ok = ChunksDict()
        self.failed = ChunksDict()
        self._chunks = chunks

    def check_finished(self, curl, seconds=0.5):
        now = time()

        if now - self._last_finish_check < seconds:
            return ChunksUnchanged(self._chunks, now)

        status = self._chunks_finish_status(now, curl.get_status())
        while status.handles_remaining:
            status = self._chunks_finish_status(now, curl.get_status())
        self._last_finish = status

        return status

    @property
    def _last_finish_check(self):
        return self._last_finish.check if self._last_finish else 0

    def _current_check_after_last(self, current_check, seconds=0.5):
        return self._last_finish or current_check - self._last_finish.check >= seconds

    def _chunks_finish_status(self, current_check, status):
        status = HttpChunksStatus(self._chunks, current_check, status)
        self._update_chunks_status(status)

        return status

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

    def is_done(self):
        return len(self.ok) >= len(self._chunks)

    @property
    def received(self):
        return sum((chunk.received for chunk in self._chunks.values()))