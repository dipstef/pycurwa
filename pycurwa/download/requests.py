from httpy.client import HttpClient, HttpyRequest, cookie_jar

from .chunks import ChunksDownloads
from .chunks.files import get_chunks_file


class DownloadRequest(HttpyRequest):

    def __init__(self, request, path, chunks=1, resume=False):
        super(DownloadRequest, self).__init__(request.method, request.url, request.headers, request.data,
                                              request.params, request.timeout, request.redirect)
        self.path = path
        self.chunks = max(chunks, 1)
        self.resume = resume


class HttpDownloadRequest(DownloadRequest):

    def __init__(self, request, path, chunks=1, resume=False, cookies=None, bucket=None):
        super(HttpDownloadRequest, self).__init__(request, path, chunks, resume)
        self._cookies = cookies
        self._bucket = bucket

    def perform(self):
        chunks_file = get_chunks_file(self, cookies=self._cookies)

        request = self._create_request(chunks_file)

        return request.perform()

    def _create_request(self, chunks_file):
        return ChunksDownloads(chunks_file, cookies=self._cookies, bucket=self._bucket)


class HttpDownloadRequests(HttpClient):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        super(HttpDownloadRequests, self).__init__(timeout)
        self._cookies = cookies
        self._bucket = bucket

    def execute(self, request, path, chunks=1, resume=False):
        return self._get_request(request, path, chunks, resume)

    def _get_request(self, request, path, chunks, resume):
        return HttpDownloadRequest(request, path, chunks, resume, self._cookies, self._bucket)