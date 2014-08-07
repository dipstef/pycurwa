from httpy.client import HttpClient, HttpyRequest, cookie_jar

from .chunks import DownloadChunks
from .chunks.files import get_chunks_file


class DownloadRequest(HttpyRequest):

    def __init__(self, request, path, chunks=1, resume=False):
        super(DownloadRequest, self).__init__(request.method, request.url, request.headers, request.data,
                                              request.params, request.timeout, request.redirect)
        self.path = path
        self.chunks = max(chunks, 1)
        self.resume = resume


class HttpDownloadRequests(HttpClient):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        super(HttpDownloadRequests, self).__init__(timeout)
        self._cookies = cookies
        self._bucket = bucket

    def execute(self, request, path, chunks=1, resume=False):
        request = DownloadRequest(request, path, chunks, resume)

        chunks_file = get_chunks_file(request, cookies=self._cookies)
        return self._create_request(chunks_file)

    def _create_request(self, chunks_file):
        return DownloadChunks(chunks_file, cookies=self._cookies, bucket=self._bucket)