import os

from httpy.error import HttpError
from httpy.http.headers.content import disposition_file_name

from .request import HttpChunk, HttpChunkCompleted

from .requests import ChunksDownload
from ..error import ChunksDownloadMismatch, FailedChunks
from ..files.download import get_chunks_file
from ..files.util import join_encoded
from ... import pycurwa


class HttpChunks(ChunksDownload):

    def __init__(self, request, cookies=None, bucket=None):
        super(HttpChunks, self).__init__(request)
        self._cookies = cookies
        self._bucket = bucket
        self._completed = False

    def _request_chunks(self, chunks_number):
        chunks_file = self._create_chunks_file(chunks_number)
        self._create_downloads(chunks_file)

    def _create_downloads(self, chunks_file):
        self._chunks_file = chunks_file

        self._create_chunks([self._chunk(chunk) for chunk in chunks_file.chunks])

        if not self.chunks and self._chunks_file.chunks:
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
        except FailedChunks:
            if not self.resume:
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
        for chunk in self.chunks:
            chunk.close()

    def _create_chunks_file(self, chunks):
        response = self._resolve_download()

        return get_chunks_file(self._request, chunks, response.headers)

    def _resolve_download(self):
        response = self._resolve_headers()
        if os.path.isdir(self.path):
            file_name = self._response_file_name(response.url, response.headers)
            self.path = join_encoded(self.path, file_name)
        return response

    def _resolve_headers(self):
        return pycurwa.head(self.url, params=self.params, headers=self.headers, data=self.data)

    def _response_file_name(self, url, headers):
        return disposition_file_name(headers) or os.path.basename(url)