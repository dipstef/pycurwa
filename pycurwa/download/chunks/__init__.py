from abc import abstractmethod
import time

from httpy.error import InvalidRangeRequest
from procol.console import print_err

from .files import get_chunks_file
from .download import HttpChunks
from .request import HttpChunk
from ..error import FailedChunks
from ..files.download import OneChunk
from ...curl.requests import RequestsRefresh


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

    @abstractmethod
    def _download(self):
        raise not NotImplementedError

    def _create_downloads(self, chunks_file):
        self._chunks_file = chunks_file
        self._chunks = self._chunks_file_downloads(chunks_file)

    def _chunks_file_downloads(self, chunks_file):
        return HttpChunks(chunks_file, self._cookies, self._bucket)


class HttpChunksDownload(ChunksFileDownload):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(HttpChunksDownload, self).__init__(chunks_file, cookies, bucket)

        self.url = chunks_file.url
        self.path = chunks_file.file_path

    def _download(self):
        try:
            return self._download_chunks()
        except FailedChunks, e:
            if len(self._chunks_file) == 1:
                raise

            for chunk_request in e.failed.values():
                print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))

            self._revert_to_one_chunk()

            return self._download_chunks()

    def _download_chunks(self):
        self._download_requests()
        return self._chunks.stats

    def _revert_to_one_chunk(self):
        print_err('Download chunks failed, fallback to single connection')
        time.sleep(2)

        self._create_downloads(self._create_one_chunk_file())

    def _create_one_chunk_file(self):
        for chunk in self._chunks_file.chunks[1:]:
            self._chunks_file.remove(chunk)

        return OneChunk(self._chunks_file.request, self._chunks_file.size, resume=self._chunks_file.resume)

    @abstractmethod
    def _download_requests(self):
        raise NotImplementedError


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

    @abstractmethod
    def _download_requests(self):
        raise NotImplementedError


class DownloadChunks(ChunksDownloads):

    def _download_requests(self):
        curl_requests = OneSessionRequests(self._chunks, refresh=0.5)

        for status in curl_requests.iterate_statuses():
            self._chunks.update(status)


class OneSessionRequests(RequestsRefresh):
    def __init__(self, requests, refresh=0.5, curl=None):
        super(OneSessionRequests, self).__init__(refresh, curl)

        for request in requests:
            self.add(request)

    def iterate_statuses(self):
        for status in super(OneSessionRequests, self).iterate_statuses():
            for request in status.completed + status.failed:
                self.close(request)

            yield status