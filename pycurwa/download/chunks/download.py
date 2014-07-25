import os
import time
from httpy import HttpRequest

from procol.console import print_err

from . import load_chunks, CreateChunksFile, OneChunk
from pycurwa.download.request import DownloadHeadersRequest
from pycurwa.request import CurlHeadersRequest
from .request import HttpChunk
from .requests import HttpChunks
from ..request import CurlRequest
from ...curl import PyCurlError


class DownloadChunks(HttpChunks):

    def __init__(self, chunks_file, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(chunks_file, cookies, bucket)

    def perform(self):
        try:
            return super(DownloadChunks, self).perform()
        except PyCurlError, e:
            if not self._is_completed():
                if not self.chunks_file.resume:
                    self.chunks_file.remove()
                raise e

    def _is_completed(self):
        try:
            return os.path.getsize(self.path) == self.size
        except OSError:
            return False

    def _handle_failed(self, status):
        for chunk, error in status.failed.values():
            print_err('Chunk %d failed: %s' % (chunk.id + 1, str(error)))

        if len(self._chunks) > 1:
            # 416 Range not satisfiable check
            print_err(('Download chunks failed, fallback to single connection | %s' % (str(status.last_error))))
            self._revert_to_one_connection()
            time.sleep(2)
        else:
            raise status.last_error

    def _revert_to_one_connection(self):
        #it returns only even element when the list is not copied, odd
        for chunk in list(self._chunks.values()):
            self._remove_chunk(chunk)

        self.chunks_file = OneChunk(self.url, self.path, self.size, resume=True)
        chunk = HttpChunk(self.url, self.chunks_file[0], self._cookies, self._bucket)

        self._chunks[0] = chunk
        self.add(chunk)

    def _remove_chunk(self, chunk):
        self.close(chunk)
        os.remove(chunk.path)


class ChunksDownload(DownloadChunks):

    def __new__(cls, file_path, download, chunks_number, resume):
        try:
            chunks = load_chunks(download.url, file_path, resume)
        except IOError, e:
            download_size = _resolve_size(download.url, download.cookies)

            chunks = CreateChunksFile(download.url, file_path, download_size, chunks_number)

        return DownloadChunks(chunks, download.cookies, download.bucket)


def _resolve_size(url, cookies=None, bucket=None):
    initial = DownloadHeadersRequest(HttpRequest('GET', url), cookies, bucket)

    try:
        headers = initial.head()
        return headers.size
    finally:
        initial.close()