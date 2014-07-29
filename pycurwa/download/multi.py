from . import HttpDownloadBase
from .chunks.download import DownloadChunks
from pycurwa.curl import CurlMulti


class MultiDownloads(HttpDownloadBase):

    def __init__(self, bucket=None):
        super(MultiDownloads, self).__init__(MultiChunks(bucket))


class MultiChunks(DownloadChunks):
    def __init__(self, bucket):
        super(MultiChunks, self).__init__(bucket)
        self._curl = CurlMulti()