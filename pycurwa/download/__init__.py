# -*- coding: utf-8 -*-

from .chunks import DownloadChunks
from .requests import HttpDownloadsRequests


class HttpDownloadBase(object):

    def __init__(self, requests):
        self._requests = requests

    def download(self, url, file_path, chunks_number=1, resume=False):
        request = self._requests.download(url, file_path, chunks_number=chunks_number, resume=resume)
        return request.perform()


class HttpDownload(HttpDownloadBase):
    def __init__(self, bucket=None):
        downloader = DownloadChunks(bucket)
        super(HttpDownload, self).__init__(HttpDownloadsRequests(downloader))

    def close(self):
        pass