from . import ChunksDict
from pycurwa.requests import MultiRequestsBase
from .request import HttpChunk
from .stats import DownloadStats
from .status import ChunksDownloadStatus
from ...error import Abort


class ChunkRequests(MultiRequestsBase):

    def __init__(self, chunks=()):
        super(ChunkRequests, self).__init__()
        self._chunks = ChunksDict()
        for chunk in chunks:
            self.add(chunk)

    def _add_request(self, chunk):
        self._chunks[chunk.id] = chunk

    def _find_request(self, handle):
        return self._chunks.get(handle.chunk_id)

    def _remove_request(self, chunk):
        del self._chunks[chunk.id]

    @property
    def chunks(self):
        return list(self._chunks.values())

    def close(self, chunk=None):
        if not chunk:
            for chunk in self:
                self.close(chunk)
        else:
            super(ChunkRequests, self).close(chunk)

    def __len__(self):
        return len(self._chunks)

    def __getitem__(self, item):
        return self._chunks[item]

    def __iter__(self):
        return iter(self._chunks.values())


class HttpChunks(ChunkRequests):

    def __init__(self, chunks, cookies=None, bucket=None):
        downloads = (HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed())
        super(HttpChunks, self).__init__(downloads)

        self.chunks_file = chunks

        self.url = chunks.url
        self.path = chunks.file_path
        self.size = chunks.size

        self._status = ChunksDownloadStatus(self.size, self._chunks)
        self._cookies = cookies
        self._bucket = bucket

        self._abort = False

    def perform(self):
        stats = self._perform()

        if self._status.received < self.size:
            raise Exception('Content size mismatch: received: %d, expected: %d' % (self._status.received, self.size))

        return stats

    def _perform(self):
        stats = DownloadStats(self.path, self.size)

        for status in self._download_checks():
            stats.update_progress(status)

            if self._abort:
                raise Abort()

        return stats

    def _download_checks(self):
        try:
            while not self._status.is_done():
                self.execute()

                status = self._get_status()

                if status.failed:
                    self._handle_failed(status)

                if not self._status.is_done():
                    yield status

                    self.select(timeout=1)
        finally:
            self.close()

    def _get_status(self):
        status = self._status.check_finished(self, seconds=0.5)

        return status

    def _handle_failed(self, status):
        raise status.last_error