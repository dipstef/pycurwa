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


class HttpChunksDownload(HttpChunks):
    def __init__(self, chunks, cookies=None, bucket=None):
        super(HttpChunksDownload, self).__init__(ChunksDownload(chunks, cookies, bucket))


class DownloadChunks(object):

    def __init__(self, bucket):
        self._bucket = bucket

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
            return self._download(chunks_file)
        except FailedChunks, e:
            if len(chunks_file.chunks) == 1:
                raise

            for chunk in e.failed.values():
                print_err('Chunk %d failed: %s' % (chunk.id + 1, str(chunk.error)))
            print_err('Download chunks failed, fallback to single connection')

            time.sleep(2)
            return self._download(_one_chunk_download(url, chunks_file))

    def _download(self, chunks_file):
        download = self._create_download(chunks_file)

        statistics = download.perform()

        chunks_file.copy_chunks()

        return statistics

    def _create_download(self, chunks_file):
        return HttpChunksDownload(chunks_file, bucket=self._bucket)


def _one_chunk_download(url, chunks_file):
    for chunk in chunks_file.chunks[1:]:
        chunks_file.remove(chunk)

    return OneChunk(url, chunks_file.file_path, chunks_file.size, resume=chunks_file.resume)