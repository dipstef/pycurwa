# -*- coding: utf-8 -*-

from .chunks import DownloadChunks, get_chunks_file
from pycurwa.download.requests import HttpDownloadRequest, HttpDownloadRequests


class HttpDownloadBase(object):

    def __init__(self, requests):
        self._requests = requests

    def download(self, url, file_path, chunks_number=1, resume=False):
        request = self._requests.download(url, file_path, chunks_number=chunks_number, resume=resume)

        return request.perform()


class HttpDownload(HttpDownloadBase):
    def __init__(self, bucket=None):
        super(HttpDownload, self).__init__(HttpDownloadRequests(bucket))