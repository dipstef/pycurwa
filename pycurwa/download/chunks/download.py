import os
import time

from httpy import HttpRequest
from procol.console import print_err

from . import ExistingDownload, NewChunks
from pycurwa.download import OneChunk
from .stats import DownloadStats
from .requests import ChunksDownloads, ChunksRefresh
from ..request import DownloadHeadersRequest
from ...error import DownloadedContentMismatch, Abort, FailedChunks
from ...util import save_join


class HttpChunks(object):

    def __init__(self, chunks, cookies=None, bucket=None):
        self._download = ChunksDownloads(chunks, cookies, bucket)

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

        for status in self._iterate_statuses():
            stats.update_progress(status)

        return stats

    def _iterate_statuses(self):
        statuses = ChunksRefresh(self._download, refresh=0.5)

        for status in statuses:
            if self._abort:
                raise Abort()

            yield status

    def __len__(self):
        return len(self._download)


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
        download = HttpChunks(chunks_file, bucket=self._bucket)

        statistics = download.perform()

        chunks_file.copy_chunks()

        return statistics


def get_chunks_file(url, file_path, chunks_number=1, resume=True, cookies=None, use_disposition=False):
    headers = None
    if use_disposition:
        headers = _resolve_headers(url, cookies)
        if headers.disposition_name:
            directory_path = os.path.dirname(file_path) if os.path.isdir(file_path) else file_path
            file_path = save_join(directory_path, headers.disposition_name)

    try:
        chunks = ExistingDownload(url, file_path, resume=resume)
    except IOError:
        if headers is None:
            headers = _resolve_headers(url, cookies)
        chunks = NewChunks(url, file_path, headers.size, chunks_number)

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


def _one_chunk_download(url, chunks_file):
    for chunk in chunks_file.chunks[1:]:
        chunks_file.remove(chunk)

    return OneChunk(url, chunks_file.file_path, chunks_file.size, resume=chunks_file.resume)