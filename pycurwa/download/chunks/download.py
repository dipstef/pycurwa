import os

from httpy.error import HttpError
from httpy.http.headers.content import disposition_file_name

from .request import HttpChunk, HttpChunkCompleted

from .requests import ChunksDownload
from ..error import ChunksDownloadMismatch
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
        self.path = chunks_file.file_path
        self.resume = chunks_file.resume
        self._chunks_file = chunks_file

        chunks = []
        for chunk in chunks_file.chunks:
            if chunk.is_completed():
                chunks.append(HttpChunkCompleted(self, chunk))
            else:
                chunks.append(HttpChunk(self, chunk, self._cookies, self._bucket))

        self._create_chunks(chunks)

        if not self.chunks and self._chunks_file.chunks:
            self._verify_completed()
            self._chunks_file.copy_chunks()

    def update(self, status):
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
        response = self._resolve_headers()

        if os.path.isdir(self.path):
            self.path = join_encoded(self.path, self._response_file_name(response.url, response.headers))

        return get_chunks_file(self._request, chunks, response.headers)

    def _resolve_headers(self):
        return pycurwa.head(self.url, params=self.params, headers=self.headers, data=self.data)

    def _response_file_name(self, url, headers):
        return disposition_file_name(headers) or os.path.basename(url)