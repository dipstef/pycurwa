import os
import time

from httpy import HttpRequest

from procol.console import print_err

from . import load_chunks, CreateChunksFile, OneChunk
from .stats import DownloadStats
from .request import HttpChunk
from .requests import ChunksDownloads
from ..request import DownloadHeadersRequest
from ...error import DownloadedContentMismatch, Abort
from ...curl import PyCurlError
from ...util import save_join


class HttpChunks(object):

    def __init__(self, chunks, cookies=None, bucket=None):
        self._download = ChunksDownloads(chunks, cookies, bucket, refresh=0.5)

        self._chunks_file = chunks

        self.url = chunks.url
        self.path = chunks.file_path
        self.size = chunks.size

        self._cookies = cookies
        self._bucket = bucket

        self._abort = False

    def perform(self):
        stats = self._perform()

        if self._download.received < self.size:
            raise DownloadedContentMismatch(self.path, self._download.received, self.size)

        return stats

    def _perform(self):
        stats = DownloadStats(self._download.chunks)

        for status in self._download.iterate_statuses():
            if self._abort:
                raise Abort()

            if status.failed:
                self._handle_failed(status)

            for chunk in status.completed.values():
                print 'Completed: ', chunk, chunk.get_speed()

            stats.update_progress(status)

        return stats

    def _handle_failed(self, status):
        raise status.last_error


class DownloadChunks(HttpChunks):

    def __init__(self, chunks, cookies=None, bucket=None):
        super(DownloadChunks, self).__init__(chunks, cookies, bucket)

    def perform(self):
        try:
            return super(DownloadChunks, self).perform()
        except PyCurlError, e:
            if not self._is_completed():
                if not self._chunks_file.resume:
                    self._chunks_file.remove()
                raise e

    def _is_completed(self):
        try:
            return os.path.getsize(self.path) == self.size
        except OSError:
            return False

    def _handle_failed(self, status):
        for chunk in status.failed.values():
            print_err('Chunk %d failed: %s' % (chunk.id + 1, str(chunk.error)))

        if len(self._chunks_file) > 1:
            print_err(('Download chunks failed, fallback to single connection | %s' % (str(status.last_error))))
            self._revert_to_one_connection()
            time.sleep(2)
        else:
            raise status.last_error

    def _revert_to_one_connection(self):
        self._download.close()
        self._chunks_file.remove(all=True)

        self._chunks_file = OneChunk(self.url, self.path, self.size, resume=True)
        self._download.add(HttpChunk(self.url, self._chunks_file[0], self._cookies, self._bucket))

    def _remove_chunk(self, chunk):
        self._download.close(chunk)
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