import time

from procol.console import print_err

from .files import get_chunks_file
from .request import HttpChunk
from .requests import ChunksDownload, ChunksDownload, MultiRefreshChunks
from ..error import ChunksDownloadMismatch, FailedChunks
from ..files.download import OneChunk


class HttpChunks(ChunksDownload):

    def __init__(self, request, chunks, cookies=None, bucket=None):
        downloads = [HttpChunk(request, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed()]
        super(HttpChunks, self).__init__(request, downloads)

        self._chunks_file = chunks

    def _update(self, status):
        super(HttpChunks, self)._update(status)

        if self.is_done():
            self.close()

            self._done_downloading(status)

    def _done_downloading(self, status):
        if not self.is_completed():
            raise ChunksDownloadMismatch(self._request, self)

        self._chunks_file.copy_chunks()

        return status

    def perform(self, **kwargs):
        try:
            return self._download(**kwargs)
        except FailedChunks:
            if not self._chunks_file.resume:
                self._chunks_file.remove()
            raise

    def _download(self, **kwargs):
        self._download_requests(**kwargs)

        return self.stats

    def _download_requests(self, **kwargs):
        raise NotImplementedError


class HttpChunksDownload(HttpChunks):

    def __init__(self, request, chunks_file, cookies=None, bucket=None):
        super(HttpChunksDownload, self).__init__(request, chunks_file, cookies=cookies, bucket=bucket)

        self.url = chunks_file.url
        self.path = chunks_file.file_path

        self._cookies = cookies
        self._bucket = bucket

    def _download(self, **kwargs):
        try:
            return super(HttpChunksDownload, self)._download(**kwargs)
        except FailedChunks, e:
            if len(self.chunks) == 1:
                raise

            for chunk_request in e.failed.values():
                print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))

            chunk = self.__class__(self._request, self._revert_to_one_chunk(), self._cookies, self._bucket)
            return chunk.perform(**kwargs)

    def _revert_to_one_chunk(self):
        print_err('Download chunks failed, fallback to single connection')
        time.sleep(2)

        for chunk in self._chunks_file.chunks[1:]:
            self._chunks_file.remove(chunk)

        return OneChunk(self.url, self.path, self._chunks_file.size, self._chunks_file.resume)


class DownloadChunks(HttpChunksDownload):

    def _download_requests(self):
        curl_requests = MultiRefreshChunks(self, refresh=0.5)

        for status in curl_requests.iterate_statuses():
            self.update(status)