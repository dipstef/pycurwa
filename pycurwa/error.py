from httpy.error import HttpResponseError, HttpError


class Abort(HttpError):
    pass


class HttpDownloadError(HttpError):
    pass


class UnexpectedContent(HttpDownloadError):
    def __init__(self, request, path, actual, expected):
        super(UnexpectedContent, self).__init__(request, path, path, actual, expected)
        message = '%s content %d different than expected %d. Try to reduce download connections.'
        self.message = message % (path, actual, expected)


class DownloadedContentMismatch(UnexpectedContent):
    def __init__(self, request, path, actual, expected):
        super(DownloadedContentMismatch, self).__init__(request, path, actual, expected)
        self.message = 'Content size mismatch% s: received: %d, expected: %d' % (path, actual, expected)


class UnexpectedCopyChunk(DownloadedContentMismatch):
    def __init__(self, request, path, actual, expected):
        super(UnexpectedCopyChunk, self).__init__(request, path, actual, expected)
        self.message = 'Not Completed %s: %d expected %d' % (path, actual, expected)


class FailedStatus(HttpResponseError):
    def __init__(self, request, status, *args, **kwargs):
        super(FailedStatus, self).__init__(request, status, *args, **kwargs)
        self.status = status
        self.failed = status.failed