from httpy.client import HttpClient, HttpyRequest, cookie_jar
from httpy.error import InvalidRangeRequest
from procol.console import print_err

from . import DownloadChunks, get_chunks_file


class DownloadRequest(HttpyRequest):

    def __init__(self, request, path, chunks=1, resume=False):
        super(DownloadRequest, self).__init__(request.method, request.url, request.headers, request.data,
                                              request.params, request.timeout, request.redirect)
        self.path = path
        self.chunks = max(chunks, 1)
        self.resume = resume


class HttpDownloadRequest(object):

    def __init__(self, request, path, chunks=1, resume=False, cookies=None, bucket=None):
        self._request = request
        self._path = path
        self._chunks = chunks
        self._resume = resume

        self._cookies = cookies
        self._bucket = bucket

    def perform(self):
        try:
            statistics = self._download(resume=self._resume)
        except InvalidRangeRequest:
            print_err('Restart without resume')
            statistics = self._download(resume=False)

        return statistics

    def _download(self, resume):
        request = DownloadRequest(self._request, self._path, self._chunks, resume)

        chunks_file = get_chunks_file(request, cookies=self._cookies)

        request = self._create_request(request, chunks_file)

        return request.perform()

    def _create_request(self, request, chunks_file):
        return DownloadChunks(request, chunks_file, cookies=self._cookies, bucket=self._bucket)


class HttpDownloadRequests(HttpClient):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        super(HttpDownloadRequests, self).__init__(timeout)
        self._cookies = cookies
        self._bucket = bucket

    def execute(self, request, path, chunks=1, resume=False):
        return self._get_request(request, path, chunks, resume)

    def _get_request(self, request, path, chunks, resume):
        return HttpDownloadRequest(request, path, chunks, resume, self._cookies, self._bucket)