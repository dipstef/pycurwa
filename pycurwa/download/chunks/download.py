import os

from httpy.error import HttpError
from httpy.http.headers.content import disposition_file_name, accepts_ranges

from .request import HttpChunk, HttpChunkCompleted

from .requests import ChunksDownload
from ..error import ChunksDownloadMismatch
from ..files.download import get_chunks_file
from ..files.util import join_encoded
from ... import pycurwa
from ...error import DownloadedContentMismatch


class HttpChunks(ChunksDownload):

    def __init__(self, request, cookies=None, bucket=None):
        super(HttpChunks, self).__init__(request)
        self._cookies = cookies
        self._bucket = bucket
        self._completed = False

    def _request_chunks(self):
        response = pycurwa.head(self.url, params=self.params, headers=self.headers, data=self.data)
        self._create_chunks(response)

    def _create_chunks(self, response):
        if os.path.isdir(self.path):
            self.path = join_encoded(self.path, self._response_file_name(response))

        chunks_number = self.chunks_requested if accepts_ranges(response.headers) else 1

        self._create_downloads(get_chunks_file(self._request, chunks_number, response.headers))

    def _create_downloads(self, chunks_file):
        self._chunks_file = chunks_file

        self._add_chunks([self._chunk(chunk) for chunk in chunks_file.chunks])

        if not self._downloads and self._chunks_file.chunks:
            self._verify_completed()
            self._chunks_file.copy_chunks()

    def _chunk(self, chunk):
        if not chunk.is_completed():
            return HttpChunk(self, chunk, self._cookies, self._bucket)
        else:
            return HttpChunkCompleted(self, chunk)

    def update(self, status):
        try:
            self._update(status)
        except BaseException, e:
            if isinstance(e, DownloadedContentMismatch) or not self.resume:
                self._chunks_file.remove()
            raise

    def _update(self, status):
        try:
            super(HttpChunks, self).update(status)

            if self._chunks.is_finished():
                self._done_downloading(status)
        except HttpError:
            self.close()
            raise

    def _done_downloading(self, status):
        self.close()
        self._verify_completed()
        self._chunks_file.copy_chunks()
        self._completed = True

    def _verify_completed(self):
        if not self._chunks.is_completed():
            raise ChunksDownloadMismatch(self._request, self._chunks)

    def close(self):
        for chunk in self._downloads:
            chunk.close()

    @staticmethod
    def _response_file_name(response):
        return disposition_file_name(response.headers) or os.path.basename(response.url)