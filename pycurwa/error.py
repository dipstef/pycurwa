class Abort(Exception):
    pass


class UnexpectedContent(Exception):
    def __init__(self, path, actual, expected):
        message = '%s content %d different than expected %d. Try to reduce download connections.'
        message = message % (path, actual, expected)
        super(UnexpectedContent, self).__init__(message)


class UnexpectedCopyChunk(UnexpectedContent):
    def __init__(self, path, actual, expected):
        super(UnexpectedCopyChunk, self).__init__(path, actual, expected)
        self.message = 'Not Completed %s: %d expected %d' % (path, actual, expected)


class DownloadedContentMismatch(UnexpectedContent):
    def __init__(self, path, actual, expected):
        super(DownloadedContentMismatch, self).__init__(path, actual, expected)
        self.message = 'Content size mismatch% s: received: %d, expected: %d' % (path, actual, expected)


class FallbackToSingleConnection(Exception):
    def __init__(self, error):
        message = 'Download chunks failed, fallback to single connection | %s' % (str(error))
        super(FallbackToSingleConnection, self).__init__(message)
        self.message = message


class FailedStatus(Exception):
    def __init__(self, status):
        super(FailedStatus, self).__init__(status)
        self.status = status
        self.failed = status.failed