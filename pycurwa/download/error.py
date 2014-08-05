from ..error import DownloadedContentMismatch, FailedStatus


class ChunksDownloadMismatch(DownloadedContentMismatch):
    def __init__(self, request, downloads):
        super(ChunksDownloadMismatch, self).__init__(request, downloads.path, downloads.size, downloads.received)


class FailedChunks(FailedStatus):
    def __init__(self, request, status, *args, **kwargs):
        super(FailedChunks, self).__init__(request, status, *args, **kwargs)
        self.message = '\n'.join('%s: %s' % (chunk_id, chunk.error) for chunk_id, chunk in status.failed.iteritems())


class FallbackToSingleConnection(FailedChunks):
    def __init__(self, request, status, *args, **kwargs):
        super(FallbackToSingleConnection, self).__init__(request, status, *args, **kwargs)
        errors = super(FallbackToSingleConnection, self).message
        self.message = 'Download chunks failed, fallback to single connection | %s' % errors


class AboveRange(DownloadedContentMismatch):
    pass