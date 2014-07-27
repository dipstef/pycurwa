from pycurwa.download.chunks.stats import DownloadStats
from ...error import Abort, DownloadedContentMismatch
from pycurwa.download.chunks.status import ChunksDownloadsStatus


class HttpChunks(object):

    def __init__(self, chunks, cookies=None, bucket=None):
        self._status = ChunksDownloadsStatus(chunks, cookies, bucket, refresh=0.5)

        self.chunks_file = chunks

        self.url = chunks.url
        self.path = chunks.file_path
        self.size = chunks.size

        self._cookies = cookies
        self._bucket = bucket

        self._abort = False

    def perform(self):
        stats = self._perform()

        if self._status.received < self.size:
            raise DownloadedContentMismatch(self.path, self._status.received, self.size)

        return stats

    def _perform(self):
        stats = DownloadStats(self._status)

        for status in self._status.iterate_statuses():
            if status.failed:
                self._handle_failed(status)

            stats.update_progress()

            if self._abort:
                raise Abort()

        return stats

    def _handle_failed(self, status):
        raise status.last_error