from httpy.error import InvalidRangeRequest
from procol.console import print_err
from . import DownloadChunks, get_chunks_file


class HttpDownloadRequest(object):

    def __init__(self, url, file_path, chunks_number=1, resume=True, cookies=None, bucket=None):
        self.url = url
        self.path = file_path
        self.chunks = max(chunks_number, 1)
        self.resume = resume

        self._cookies = cookies
        self._bucket = bucket

    def perform(self):
        try:
            statistics = self._download(resume=self.resume)
        except InvalidRangeRequest:
            print_err('Restart without resume')
            statistics = self._download(resume=False)

        return statistics

    def _download(self, resume):
        chunks_file = get_chunks_file(self.url, self.path, self.chunks, resume=resume, cookies=self._cookies)

        request = self._create_request(chunks_file)

        return request.perform()

    def _create_request(self, chunks_file):
        return DownloadChunks(chunks_file, cookies=self._cookies, bucket=self._bucket)


class HttpDownloadRequests(object):

    def __init__(self, cookies=None, bucket=None):
        self._cookies = cookies
        self._bucket = bucket

    def download(self, url, file_path, chunks_number=1, resume=False):
        request = self._request(url, file_path, chunks_number=chunks_number, resume=resume)

        return request

    def _request(self, url, file_path, chunks_number, resume):
        return HttpDownloadRequest(url, file_path, chunks_number, resume, self._cookies, self._bucket)