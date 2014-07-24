from collections import namedtuple
from time import time
from pycurwa.curl.error import CurlWriteError, CurlError
from pycurwa.download.chunks import ChunksDict
from pycurwa.error import BadHeader


class FailedChunk(namedtuple('FailedChunk', ('chunk', 'error'))):

    @property
    def id(self):
        return self.chunk.id


class HttpChunksStatus(object):

    def __init__(self, chunks, ok_chunks, failed_chunks, handles_remaining):
        ok, failed = ChunksDict(ok_chunks), ChunksDict(failed_chunks)

        for chunk in ok_chunks:
            try:
                chunk.verify_header()
            except BadHeader, e:
                del ok[chunk.id]
                failed[chunk.id] = (chunk, e)

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
        self.check = time()

    @property
    def last_error(self):
        return self.failed.values()[-1].error

    @property
    def chunks_received(self):
        return [chunk.received for chunk in self._chunks.values()]


class ChunksDownloadStatus(object):

    def __init__(self, chunks):
        self._last_status = None
        self._current_status = None

        self.ok = ChunksDict()
        self.failed = ChunksDict()
        self._chunks = chunks

    def update_chunks_status(self, handles_remaining, ok, failed):
        ok = [self._get_chunk(curl) for curl in ok]
        failed = [FailedChunk(self._get_chunk(curl), CurlError(errno, msg)) for curl, errno, msg in failed]

        status = HttpChunksStatus(self._chunks, ok, failed, handles_remaining)
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

        self._last_status = self._current_status
        self._current_status = status

    def _get_chunk(self, handle):
        for chunk in self._chunks.values():
            if chunk.curl == handle:
                return chunk
        raise Exception('Handle not Found', handle)


    @property
    def received(self):
        return sum(chunk.received for chunk in self._chunks.values())

    @property
    def chunks_received(self):
        return [chunk.received for chunk in self._chunks.values()]

    def is_done(self):
        return len(self.ok) >= len(self._chunks)

    def updated_less_than(self, seconds=0.5):
        return not self._last_status or self._last_status.check + seconds < self._current_status.check
