from httpy.error import InvalidRangeRequest
from procol.console import print_err


class HttpDownloadRequest(object):

    def __init__(self, downloader, url, file_path, chunks_number, resume=False):
        self._downloader = downloader
        self._url = url
        self._path = file_path
        self._chunks_number = max(1, chunks_number)
        self._resume = resume

    def perform(self):
        try:
            statistics = self._download(resume=self._resume)
        except InvalidRangeRequest:
            print_err('Restart without resume')
            statistics = self._download(resume=False)

        return statistics

    def _download(self, resume):
        return self._downloader.download(self._url, self._path, chunks_number=self._chunks_number, resume=resume)


class HttpDownloadsRequests(object):

    def __init__(self, downloader):
        self._downloader = downloader

    def download(self, url, file_path, chunks_number=1, resume=False):
        return HttpDownloadRequest(self._downloader, url, file_path, chunks_number, resume)