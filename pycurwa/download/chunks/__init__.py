import time

from httpy.error import InvalidRangeRequest
from procol.console import print_err

from .files import get_chunks_file
from .download import HttpChunks
from .request import HttpChunk
from ..error import FailedChunks
from ..files.download import OneChunk
from ...multi.requests import OneSessionRequests


class ChunksFileDownload(object):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        self._cookies = cookies
        self._bucket = bucket

        self._create_downloads(chunks_file)

    def perform(self):
        try:
            return self._download()
        except FailedChunks:
            if not self._chunks_file.resume:
                self._chunks_file.remove()
            raise

    def _download(self):
        return self._chunks.perform()

    def _create_downloads(self, chunks_file):
        self._chunks_file = chunks_file
        self._chunks = self._create_http_chunks(chunks_file)

    def _create_http_chunks(self, chunks_file):
        return DownloadChunks(chunks_file, self._cookies, self._bucket)


class HttpChunksDownload(ChunksFileDownload):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(HttpChunksDownload, self).__init__(chunks_file, cookies, bucket)

        self.url = chunks_file.url
        self.path = chunks_file.file_path

    def _download(self):
        try:
            return super(HttpChunksDownload, self)._download()
        except FailedChunks, e:
            if len(self._chunks_file) == 1:
                raise

            for chunk_request in e.failed.values():
                print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))

            self._revert_to_one_chunk()

            return super(HttpChunksDownload, self)._download()

    def _revert_to_one_chunk(self):
        print_err('Download chunks failed, fallback to single connection')
        time.sleep(2)

        self._create_downloads(self._create_one_chunk_file())

    def _create_one_chunk_file(self):
        for chunk in self._chunks_file.chunks[1:]:
            self._chunks_file.remove(chunk)

        return OneChunk(self._chunks_file.request, self._chunks_file.size, resume=self._chunks_file.resume)


class ChunksDownloads(HttpChunksDownload):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(ChunksDownloads, self).__init__(chunks_file, cookies, bucket)

    def perform(self):
        try:
            return super(ChunksDownloads, self).perform()
        except InvalidRangeRequest:
            if self._chunks_file.resume:
                return self._no_resume_download()
            raise

    def _no_resume_download(self):
        self._chunks_file.resume = False
        self._create_downloads(self._chunks_file)
        return super(ChunksDownloads, self).perform()


class DownloadChunks(HttpChunks):

    def perform(self):
        curl_requests = OneSessionRequests(self, refresh=0.5)

        for status in curl_requests.iterate_statuses():
            self.update(status)

        return self.stats