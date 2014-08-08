import time

from httpy.error import InvalidRangeRequest

from procol.console import print_err

from .download import HttpChunks
from .request import HttpChunk
from ..error import FailedChunks
from ..files.download import OneChunk


class ChunksFileDownload(HttpChunks):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        self._cookies = cookies
        self._bucket = bucket
        super(ChunksFileDownload, self).__init__(chunks_file, cookies, bucket)

    def _update(self, status):
        try:
            super(ChunksFileDownload, self)._update(status)
        except FailedChunks:
            if not self._chunks_file.resume:
                self._chunks_file.remove()
            raise


class RetryChunks(ChunksFileDownload):

    def _update(self, status):
        try:
            super(RetryChunks, self)._update(status)
        except InvalidRangeRequest:
            if self._chunks_file.resume:
                return self._no_resume_download()
            raise

    def _no_resume_download(self):
        self._chunks_file.resume = False
        self._retry_chunks(self._chunks_file)

    def _retry_chunks(self, chunks_file):
        self.close()
        self._reset(chunks_file)
        self._submit()
        time.sleep(2)

    def _reset(self, chunks_file):
        super(RetryChunks, self).__init__(chunks_file, self._cookies, self._bucket)

    def _submit(self):
        raise NotImplementedError


class ChunksDownloads(RetryChunks):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(ChunksDownloads, self).__init__(chunks_file, cookies, bucket)

    def _update(self, status):
        try:
            return super(ChunksDownloads, self)._update(status)
        except FailedChunks, e:
            if len(self._chunks_file) == 1:
                raise

            for chunk_request in e.failed.values():
                print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))

            self._revert_to_one_chunk()

    def _revert_to_one_chunk(self):
        print_err('fallback to single connection')
        self._retry_chunks(self._create_one_chunk_file())

    def _create_one_chunk_file(self):
        for chunk in self._chunks_file.chunks[1:]:
            self._chunks_file.remove(chunk)

        return OneChunk(self._chunks_file.request, self._chunks_file.size, resume=self._chunks_file.resume)