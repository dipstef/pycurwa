from ...error import DownloadedContentMismatch


class UnexpectedCopyChunk(DownloadedContentMismatch):
    def __init__(self, request, path, actual, expected):
        super(UnexpectedCopyChunk, self).__init__(request, path, actual, expected)
        self.message = 'Not Completed %s: %d expected %d' % (path, actual, expected)