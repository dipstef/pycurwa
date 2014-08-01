import time

from procol.console import print_err

from .chunks import get_chunks_file
from pycurwa.download.files.download import OneChunk
from .request import HttpChunk
from .requests import ChunksDownload, ChunksDownload, MultiRefreshChunks
from .error import ChunksDownloadMismatch, FailedChunks


class HttpChunks(ChunksDownload):

    def __init__(self, chunks, cookies=None, bucket=None):
        downloads = [HttpChunk(chunks.url, chunk, cookies, bucket) for chunk in chunks if not chunk.is_completed()]

        super(HttpChunks, self).__init__(downloads)
        self._chunks_file = chunks

    def perform(self, **kwargs):
        try:
            return self._download(**kwargs)
        except FailedChunks:
            if not self._chunks_file.resume:
                self._chunks_file.remove()
            raise

    def _download(self, **kwargs):
        stats = self._download_requests(**kwargs)

        if not self.is_completed():
            raise ChunksDownloadMismatch(self)

        self._chunks_file.copy_chunks()

        return stats

    def _download_requests(self, **kwargs):
        raise NotImplementedError


class HttpChunksDownload(HttpChunks):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(HttpChunksDownload, self).__init__(chunks_file, cookies=cookies, bucket=bucket)

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

            chunk = self.__class__(self._revert_to_one_chunk(), self._cookies, self._bucket)
            return chunk.perform(**kwargs)

    def _revert_to_one_chunk(self):
        print_err('Download chunks failed, fallback to single connection')
        time.sleep(2)

        for chunk in self._chunks_file.chunks[1:]:
            self._chunks_file.remove(chunk)

        return OneChunk(self.url, self.path, self._chunks_file.size, self._chunks_file.resume)


class DownloadChunks(HttpChunksDownload):

    def _download_requests(self):
        requests = MultiRefreshChunks(self, refresh=0.5)

        return self._perform(requests)

    def _iterate_updates(self, requests):
        try:
            for status in requests.iterate_statuses():
                self.update(status)
                yield status
        finally:
            self.close()