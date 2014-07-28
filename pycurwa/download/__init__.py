# -*- coding: utf-8 -*-
from httpy.error import InvalidRangeRequest
from procol.console import print_err

from .chunks import Chunks, OneChunk
from .chunks.download import get_chunks_file, DownloadChunks


class HttpDownload(object):

    def __init__(self, bucket=None):
        self._chunks = DownloadChunks(bucket)

    def download(self, url, file_path, chunks_number=1, resume=False):
        chunks_number = max(1, chunks_number)

        try:
            statistics = self._chunks.download(url, file_path, chunks_number, resume)
        except InvalidRangeRequest:
            print_err('Restart without resume')
            statistics = self._chunks.download(url, file_path, chunks_number, resume=False)

        return statistics