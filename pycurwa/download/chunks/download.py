import time

from procol.console import print_err

from . import load_chunks, CreateChunksFile, OneChunk, ChunkFile
from .request import FirstChunk, HttpChunks, HttpChunk
from ...curl import CurlMulti, perform_multi


class DownloadChunks(HttpChunks):

    def __init__(self, chunks, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(chunks, cookies, bucket)

    def download_checks(self):
        while not self._status.is_done():
            perform_multi(self.curl)

            status = self._update_status()

            if status.failed:
                self._check_chunks(status)

            if not self._status.is_done():
                yield status

                self.curl.select(1)

    def _check_chunks(self, status):
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
            del self._chunks[chunk.id]

        self.chunks_file = OneChunk(self.url, self.path, self.size, resume=True)
        chunk = HttpChunk(self.url, self.chunks_file[0], self._cookies, self._bucket)
        self._chunks[0] = chunk
        self.curl.add_handle(chunk.curl)


class ChunksDownload(DownloadChunks):

    def __new__(cls, file_path, download, chunks_number, resume):
        try:
            chunks = load_chunks(download.url, file_path, resume)
        except IOError, e:
            download_size = _resolve_size(file_path, download)

            chunks = CreateChunksFile(download.url, file_path, download_size, chunks_number)

        return DownloadChunks(chunks, download.cookies, download.bucket)


def _resolve_size(file_path, download):
    chunk = ChunkFile(1, 1, '%s.chunk%s' % (file_path, 0), (0, 1024))

    initial = FirstChunk(download.url, chunk, download.cookies, download.bucket)

    with CurlMulti() as curl:
        curl.add_handle(initial.curl)

        while not initial.size:
            curl.perform()
            curl.select(1)

        curl.remove_handle(initial.curl)
        initial.close()

    return initial.size