# -*- coding: utf-8 -*-
from httpy.error import InvalidRangeRequest
from procol.console import print_err

from .chunks import DownloadChunks


class HttpDownloadRequest(object):

    def __init__(self, url, file_path, chunks_number=1, resume=True, bucket=None):
        self.url = url
        self.path = file_path
        self.chunks = max(chunks_number, 1)
        self.resume = resume
        self._bucket = bucket

    def perform(self):
        try:
            statistics = self._download(resume=self.resume)
        except InvalidRangeRequest:
            print_err('Restart without resume')
            statistics = self._download(resume=False)

        return statistics

    def _download(self, resume):
        request = self._create_request(resume)

        return request.perform()

    def _create_request(self, resume):
        return DownloadChunks(self.url, self.path, self.chunks, resume, self._bucket)


class HttpDownloadRequests(object):

    def __init__(self, bucket=None):
        self._bucket = bucket

    def download(self, url, file_path, chunks_number=1, resume=False):
        request = self._request(url, file_path, chunks_number=chunks_number, resume=resume)

        return request

    def _request(self, url, file_path, chunks_number, resume):
        return HttpDownloadRequest(url, file_path, chunks_number, resume, self._bucket)


class HttpDownloadBase(object):

    def __init__(self, requests):
        self._requests = requests

    def download(self, url, file_path, chunks_number=1, resume=False):
        request = self._requests.download(url, file_path, chunks_number=chunks_number, resume=resume)

        return request.perform()


class HttpDownload(HttpDownloadBase):
    def __init__(self, bucket=None):
        super(HttpDownload, self).__init__(HttpDownloadRequests(bucket))