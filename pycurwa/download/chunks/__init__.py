import time

from procol.console import print_err

from .chunks import get_chunks_file
from pycurwa.download.files.download import OneChunk
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

    def __init__(self, chunks_file, cookies=None, bucket=None):
        self._cookies = cookies
        self._bucket = bucket

        downloads = self._get_chunks_download(chunks_file)

        self._downloads = HttpChunks(downloads)
        self._chunks_file = chunks_file

    def perform(self):
        try:
            return self._download()
        except FailedChunks:
            if not self._chunks_file.resume:
                self._chunks_file.remove()
            raise

    def _download(self):
        statistics = self._downloads.perform()

        self._chunks_file.copy_chunks()

        return statistics

    def _get_chunks_download(self, chunks_file):
        return ChunksDownload(chunks_file)

    @property
    def chunks(self):
        return self._chunks_file


class DownloadChunks(ChunksFileDownload):

    def __init__(self, url, path, chunks_number=1, resume=True, bucket=None):
        chunks_file = get_chunks_file(url, path, chunks_number, resume=resume)

        super(DownloadChunks, self).__init__(chunks_file, bucket=bucket)

        self.url = url
        self.path = path
        self.number = len(self._chunks_file)
        self.resume = self._chunks_file.resume

    def _download(self):
        try:
            return super(DownloadChunks, self)._download()
        except FailedChunks, e:
            if len(self.chunks) == 1:
                raise

            for chunk_request in e.failed.values():
                print_err('Chunk %d failed: %s' % (chunk_request.id + 1, str(chunk_request.error)))

            one_chunk_download = ChunksFileDownload(self._revert_to_one_chunk(), self._cookies, self._bucket)

            return one_chunk_download.perform()

    def _revert_to_one_chunk(self):

        print_err('Download chunks failed, fallback to single connection')
        time.sleep(2)
        one_chunk = _one_chunk_download(self.url, self._chunks_file)
        return one_chunk


def _one_chunk_download(url, chunks_file):
    for chunk in chunks_file.chunks[1:]:
        chunks_file.remove(chunk)

    return OneChunk(url, chunks_file.file_path, chunks_file.size, resume=chunks_file.resume)