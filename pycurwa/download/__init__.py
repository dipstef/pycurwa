from .chunks import DownloadChunks, get_chunks_file
from .requests import HttpDownloadRequest, HttpDownloadRequests


class HttpDownloadBase(object):

    def __init__(self, requests):
        self._requests = requests

    def download(self, url, file_path, chunks_number=1, resume=False):
        request = self._requests.get(url, path=file_path, chunks=chunks_number, resume=resume)

        return request.perform()


class HttpDownload(HttpDownloadBase):
    def __init__(self, cookies=None, bucket=None):
        super(HttpDownload, self).__init__(HttpDownloadRequests(cookies, bucket))