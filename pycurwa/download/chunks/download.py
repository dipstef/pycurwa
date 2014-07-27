import os
import time

from httpy import HttpRequest

from procol.console import print_err

from . import load_chunks, CreateChunksFile, OneChunk
from pycurwa.download.request import DownloadHeadersRequest
from .request import HttpChunk
from .requests import HttpChunks
from ...curl import PyCurlError
from ...util import save_join


class DownloadChunks(HttpChunks):

    def __init__(self, chunks, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(chunks, cookies, bucket)

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
        curl_errors = []
        for chunk, error in status.failed.values():
            print_err('Chunk %d failed: %s' % (chunk.id + 1, str(error)))
            if isinstance(error, PyCurlError):
                curl_errors.append(error)

        if curl_errors and len(self._chunks) > 1:
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


def get_chunks_file(url, file_path, chunks_number=1, resume=True, cookies=None, use_disposition=False):
    headers = None
    if use_disposition:
        headers = _resolve_headers(url, cookies)
        if headers.disposition_name:
            directory_path = os.path.dirname(file_path) if os.path.isdir(file_path) else file_path
            file_path = save_join(directory_path, headers.disposition_name)

    try:
        chunks = load_chunks(url, file_path, resume=resume)
    except IOError:
        if headers is None:
            headers = _resolve_headers(url, cookies)
        chunks = CreateChunksFile(url, file_path, headers.size, chunks_number)

    return chunks


def _resolve_size(url, cookies=None, bucket=None):
    headers = _resolve_headers(url, cookies, bucket)

    return headers.size


def _resolve_headers(url, cookies=None, bucket=None):
    initial = DownloadHeadersRequest(HttpRequest('HEAD', url), cookies, bucket)
    try:
        return initial.head()
    finally:
        initial.close()