from .chunks import DownloadChunks, get_chunks_file
from .requests import HttpDownloadRequest, HttpDownloadRequests


class HttpDownload(HttpDownloadRequests):

    def execute(self, request, path, chunks=1, resume=False):
        download = super(HttpDownload, self).execute(request, path, chunks, resume)
        return download.perform()