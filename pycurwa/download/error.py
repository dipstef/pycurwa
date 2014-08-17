from ..error import DownloadedContentMismatch, FailedStatus


class ChunksDownloadMismatch(DownloadedContentMismatch):
    def __init__(self, request, chunks):
        super(ChunksDownloadMismatch, self).__init__(request, request.path, chunks.received, chunks.size)


class FailedChunks(FailedStatus):
    def __init__(self, request, status, *args, **kwargs):
        super(FailedChunks, self).__init__(request, status, *args, **kwargs)
        self.message = '\n'.join('%s: %s' % (chunk_id, chunk.error) for chunk_id, chunk in status.failed.iteritems())

    def __str__(self):
        return self.message


class FallbackToSingleConnection(FailedChunks):
    def __init__(self, request, status, *args, **kwargs):
        super(FallbackToSingleConnection, self).__init__(request, status, *args, **kwargs)
        errors = super(FallbackToSingleConnection, self).message
        self.message = 'Download chunks failed, fallback to single connection | %s' % errors


class AboveRange(DownloadedContentMismatch):
    pass