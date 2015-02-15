import time
from httpy.connection.error import NotConnected
from httpy.error import InvalidRangeRequest
from procol.console import print_err

from .download import HttpChunks
from .error import FailedChunks, MaxAttemptsReached
from .request import HttpChunk
from ..files.download import create_chunks_file


class RetryChunks(HttpChunks):

    def __init__(self, request, cookies=None, bucket=None, max_attempts=5):
        super(RetryChunks, self).__init__(request, cookies, bucket)
        self._max_attempts = max_attempts
        self._attempts = 0

    def _update(self, status):
        try:
            super(RetryChunks, self)._update(status)
        except InvalidRangeRequest:
            if self.resume:
                self._no_resume_download()
            else:
                raise
        except FailedChunks, e:
            if not e.disconnected():
                self._attempts += 1

            if self._attempts < self._max_attempts:
                raise
            raise MaxAttemptsReached(e.request, e.status)

    def _no_resume_download(self):
        self.resume = False
        self._chunks_file.resume = False
        self._retry_chunks(self._chunks_file)

    def _retry_chunks(self, chunks_file):
        self.close()
        self._create_downloads(chunks_file)
        self._submit()
        time.sleep(2)

    def _submit(self):
        raise NotImplementedError


class ChunksDownloads(RetryChunks):

    def _get_head_response(self):
        while True:
            try:
                return self._resolve_download()
            except NotConnected:
                print_err('Not connected while resolving: ', self._request)
                time.sleep(1)

    def _resolve_download(self):
        return super(ChunksDownloads, self)._get_head_response()

    def _update(self, status):
        try:
            return super(ChunksDownloads, self)._update(status)
        except FailedChunks, e:
            if e.disconnected():
                print_err('Disconnected: while downloading, retrying %s' % self._request)
                self._retry_chunks(self._chunks_file)
            elif e.connection_timeout() and self._chunks.chunks_received.sum() > 0:
                print_err('Connection timeout: retrying %s %d time' % (self._request, self._attempts))
                self._retry_chunks(self._chunks_file)
            elif e.incomplete_read():
                print_err('Incomplete read: retrying %s %d time' % (self._request, self._attempts))
                self._retry_chunks(self._chunks_file)
            elif len(self._chunks_file) == 1 or not e.available:
                raise
            else:
                for chunk_request in e.failed:
                    print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))
                self._revert_to_one_chunk()

    def _revert_to_one_chunk(self):
        print_err('fallback to single connection')
        for chunk in self._chunks_file.chunks[1:]:
            self._chunks_file.remove(chunk)

        self._retry_chunks(create_chunks_file(self._request, chunks_number=1, size=self.size, resume=self.resume))

    def _has_downloaded(self):
        self._chunks