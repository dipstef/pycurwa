import time
from procol.console import print_err

from .chunk import Chunk, ChunkFile
from .download import get_chunks_file, OneChunk
from .requests import ChunksDownload
from .error import ChunksDownloadMismatch, FailedChunks


class HttpChunks(object):

    def __init__(self, downloads):
        self._downloads = downloads

    def perform(self):
        stats = self._downloads.perform()

        if not self._downloads.is_completed():
            raise ChunksDownloadMismatch(self._downloads)

        return stats

    def __len__(self):
        return len(self._downloads)


class ChunksFileDownload(object):

    def __init__(self, cookies=None, bucket=None):
        self._cookies = cookies
        self._bucket = bucket

    def download(self, chunks_file):
        chunks_download = HttpChunks(self._get_chunks(chunks_file))

        statistics = chunks_download.perform()

        chunks_file.copy_chunks()

        return statistics

    def _get_chunks(self, chunks_file):
        return ChunksDownload(chunks_file, self._cookies, self._bucket)


class HttpChunksRequest(object):

    def __init__(self, downloader):
        self._downloader = downloader

    def download(self, url, path, chunks_number=1, resume=False):
        chunks_file = get_chunks_file(url, path, chunks_number, resume=resume)

        try:
            return self._download_chunks(url, chunks_file)
        except FailedChunks:
            if not chunks_file.resume:
                chunks_file.remove()
            raise

    def _download_chunks(self, url, chunks_file):
        try:
            return self._downloader.download(chunks_file)
        except FailedChunks, e:
            if len(chunks_file.chunks) == 1:
                raise

            for chunk_request in e.failed.values():
                print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))

            print_err('Download chunks failed, fallback to single connection')
            time.sleep(2)

            return self._downloader.download(_one_chunk_download(url, chunks_file))


class DownloadChunks(HttpChunksRequest):
    def __init__(self, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(ChunksFileDownload(cookies, bucket))


def _one_chunk_download(url, chunks_file):
    for chunk in chunks_file.chunks[1:]:
        chunks_file.remove(chunk)

    return OneChunk(url, chunks_file.file_path, chunks_file.size, resume=chunks_file.resume)