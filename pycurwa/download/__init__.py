# -*- coding: utf-8 -*-
from httpy.error import InvalidRangeRequest
from procol.console import print_err

from .chunks import DownloadChunks


class HttpDownloadBase(object):

    def __init__(self, chunks_download):
        self._chunks = chunks_download

    def download(self, url, file_path, chunks_number=1, resume=False):
        chunks_number = max(1, chunks_number)

        try:
            statistics = self._chunks.download(url, file_path, chunks_number, resume)
        except InvalidRangeRequest:
            print_err('Restart without resume')
            statistics = self._chunks.download(url, file_path, chunks_number, resume=False)

        return statistics


class HttpDownload(HttpDownloadBase):
    def __init__(self, bucket=None):
        super(HttpDownload, self).__init__(DownloadChunks(bucket))

    def close(self):
        pass