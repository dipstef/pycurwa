# -*- coding: utf-8 -*-
from httpy.error import InvalidRangeRequest
from procol.console import print_err

from .chunks import Chunks
from .chunks.download import get_chunks_file, DownloadChunks


class HttpDownload(object):

    def __init__(self, bucket=None):
        self._bucket = bucket

    def download(self, url, file_path, chunks_number=1, resume=False):
        chunks_number = max(1, chunks_number)

        try:
            statistics = self._download(url, file_path, chunks_number, resume)
        except InvalidRangeRequest:
            print_err('Restart without resume')
            statistics = self._download(url, file_path, chunks_number, resume=False)

        return statistics

    def _download(self, url, file_path, chunks_number, resume):
        chunks_file = get_chunks_file(url, file_path, chunks_number, resume=resume)

        download = DownloadChunks(chunks_file, bucket=self._bucket)

        statistics = download.perform()

        chunks_file.copy_chunks()

        return statistics