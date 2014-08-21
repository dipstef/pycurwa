import time
from httpy.connection.error import NotConnected
from httpy.error import InvalidRangeRequest
from procol.console import print_err

from .download import HttpChunks
from .request import HttpChunk
from ..error import FailedChunks
from ..files.download import create_chunks_file


class RetryChunks(HttpChunks):

    def _update(self, status):
        try:
            super(RetryChunks, self)._update(status)
        except InvalidRangeRequest:
            if self.resume:
                self._no_resume_download()
            else:
                raise

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