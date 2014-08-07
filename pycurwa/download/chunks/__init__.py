import time

from httpy.error import InvalidRangeRequest

from procol.console import print_err

from .files import get_chunks_file
from .download import HttpChunks, HttpChunksRequests
from .request import HttpChunk
from ..error import FailedChunks
from ..files.download import OneChunk
from ...curl.requests import RequestsRefresh


class ChunksFileDownload(object):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        self._requests = requests
        self._cookies = cookies
        self._bucket = bucket

        self._create_downloads(chunks_file)

    def update(self, status):
        self._update(status)

    def _update(self, status):
        try:
            self._chunks.update(status)
        except FailedChunks:
            if not self._chunks_file.resume:
                self._chunks_file.remove()
            raise

    def _create_downloads(self, chunks_file):
        self._chunks_file = chunks_file
        self._chunks = self._create_http_chunks(chunks_file)

    def _create_http_chunks(self, chunks_file):
        return HttpChunksRequests(self._requests, chunks_file, self._cookies, self._bucket)

    def perform(self):
        self._chunks.submit()
        self._wait_termination()
        return self._chunks.stats

    def __iter__(self):
        return iter(self._chunks)

    def _wait_termination(self):
        pass


class HttpChunksDownload(ChunksFileDownload):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(HttpChunksDownload, self).__init__(requests, chunks_file, cookies, bucket)

    def _update(self, status):
        try:
            return super(HttpChunksDownload, self)._update(status)
        except FailedChunks, e:
            if len(self._chunks_file) == 1:
                raise

            _log_fall_back(e)
            self._revert_to_one_chunk()

    def _revert_to_one_chunk(self):
        self._retry_chunks(self._create_one_chunk_file())

    def _retry_chunks(self, chunks_file):
        self._chunks.close()
        self._create_downloads(chunks_file)
        self._chunks.submit()
        time.sleep(2)

    def _create_one_chunk_file(self):
        for chunk in self._chunks_file.chunks[1:]:
            self._chunks_file.remove(chunk)

        return OneChunk(self._chunks_file.request, self._chunks_file.size, resume=self._chunks_file.resume)


def _log_fall_back(error):
    for chunk_request in error.failed.values():
        print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))
    print_err('fallback to single connection')


class ChunksDownloads(HttpChunksDownload):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(ChunksDownloads, self).__init__(requests, chunks_file, cookies, bucket)

    def _update(self, status):
        try:
            super(ChunksDownloads, self)._update(status)
        except InvalidRangeRequest:
            if self._chunks_file.resume:
                return self._no_resume_download()
            raise

    def _no_resume_download(self):
        self._chunks_file.resume = False
        self._retry_chunks(self._chunks_file)


class DownloadChunks(ChunksDownloads):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(RequestsRefresh(refresh=0.5), chunks_file, cookies, bucket)

    def _wait_termination(self):
        for status in self._requests.iterate_statuses():
            for chunk in status.completed:
                self._requests.close(chunk)

            self.update(status)

        return self._chunks.stats