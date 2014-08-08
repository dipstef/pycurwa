import time

from httpy.error import InvalidRangeRequest

from procol.console import print_err

from .download import HttpChunks, HttpChunksRequests
from .request import HttpChunk
from ..error import FailedChunks
from ..files.download import OneChunk


class ChunksFileDownload(HttpChunksRequests):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        self._cookies = cookies
        self._bucket = bucket
        super(ChunksFileDownload, self).__init__(requests, chunks_file, cookies, bucket)

    def _update(self, status):
        try:
            super(ChunksFileDownload, self)._update(status)
        except FailedChunks:
            if not self._chunks_file.resume:
                self._chunks_file.remove()
            raise

    def _submit(self):
        for chunk in self.chunks:
            self._requests.add(chunk)

    def close(self):
        for chunk in self.chunks:
            self._requests.close(chunk)


class HttpChunksDownload(ChunksFileDownload):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(HttpChunksDownload, self).__init__(requests, chunks_file, cookies, bucket)

    def update(self, status):
        try:
            return super(HttpChunksDownload, self).update(status)
        except FailedChunks, e:
            if len(self._chunks_file) == 1:
                raise

            for chunk_request in e.failed.values():
                print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))

            self._revert_to_one_chunk()

    def _revert_to_one_chunk(self):
        print_err('fallback to single connection')
        self._retry_chunks(self._create_one_chunk_file())

    def _retry_chunks(self, chunks_file):
        self.close()
        self._reset(chunks_file)
        self._submit()
        time.sleep(2)

    def _reset(self, chunks_file):
        super(HttpChunksDownload, self).__init__(self._requests, chunks_file, self._cookies, self._bucket)

    def _create_one_chunk_file(self):
        for chunk in self._chunks_file.chunks[1:]:
            self._chunks_file.remove(chunk)

        return OneChunk(self._chunks_file.request, self._chunks_file.size, resume=self._chunks_file.resume)


class ChunksDownloads(HttpChunksDownload):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(ChunksDownloads, self).__init__(requests, chunks_file, cookies, bucket)

    def update(self, status):
        try:
            super(ChunksDownloads, self).update(status)
        except InvalidRangeRequest:
            if self._chunks_file.resume:
                return self._no_resume_download()
            raise

    def _no_resume_download(self):
        self._chunks_file.resume = False
        self._retry_chunks(self._chunks_file)

    def perform(self):
        self._submit()
        self._wait_termination()
        return self.stats

    def _wait_termination(self):
        pass