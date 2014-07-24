from collections import namedtuple, OrderedDict
from time import time

from pycurwa.curl.error import CurlWriteError, CurlError
from pycurwa.download.chunks import ChunksDict
from pycurwa.error import BadHeader


class FailedChunk(namedtuple('FailedChunk', ('chunk', 'error'))):

    @property
    def id(self):
        return self.chunk.id


class HttpChunksStatus(object):

    def __init__(self, chunks, check, ok_chunks, failed_chunks, handles_remaining):
        ok, failed = ChunksDict(ok_chunks), ChunksDict(failed_chunks)

        for chunk in ok_chunks:
            try:
                chunk.verify_header()
            except BadHeader, e:
                del ok[chunk.id]
                failed[chunk.id] = FailedChunk(chunk, e)

        for chunk, error in failed_chunks:
            if isinstance(error, CurlWriteError):
                #double check header
                try:
                    chunk.verify_header()
                    del failed[chunk.id]
                    ok[chunk.id] = chunk
                except BadHeader, e:
                    pass

        self._chunks = chunks
        self.ok = ok
        self.failed = failed
        self.handles_remaining = handles_remaining
        self.check = check

    @property
    def last_error(self):
        return self.failed.values()[-1].error if self.failed else None

    @property
    def chunks_received(self):
        return OrderedDict((chunk_id, chunk.received) for chunk_id, chunk in self._chunks.iteritems())

    @property
    def chunks_speed(self):
        return OrderedDict((chunk_id, chunk.get_speed()) for chunk_id, chunk in self._chunks.iteritems())


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
            return HttpChunksStatus(self._chunks, now, self._chunks.values(), [], [])

        status = self._chunks_finish_status(now, *curl.info_read())
        while status.handles_remaining:
            status = self._chunks_finish_status(now, *curl.info_read())
        self._last_finish = status

        return status


    @property
    def _last_finish_check(self):
        return self._last_finish.check if self._last_finish else 0

    def _current_check_after_last(self, current_check, seconds=0.5):
        return self._last_finish or current_check - self._last_finish.check >= seconds

    def _chunks_finish_status(self, current_check, handles_remaining, ok, failed):
        ok = [self._get_chunk(curl) for curl in ok]
        failed = [FailedChunk(self._get_chunk(curl), CurlError(errno, msg)) for curl, errno, msg in failed]

        status = HttpChunksStatus(self._chunks, current_check, ok, failed, handles_remaining)
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

    def _get_chunk(self, handle):
        for chunk in self._chunks.values():
            if chunk.curl == handle:
                return chunk
        raise Exception('Handle not Found', handle)

    def is_done(self):
        return len(self.ok) >= len(self._chunks)

    @property
    def received(self):
        return sum((chunk.received for chunk in self._chunks.values()))