from pycurwa.error import DownloadedContentMismatch


class ChunksDownloadMismatch(DownloadedContentMismatch):
    def __init__(self, downloads):
        super(ChunksDownloadMismatch, self).__init__(downloads.path, downloads.size, downloads.received)