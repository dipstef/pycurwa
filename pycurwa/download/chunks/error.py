from httpy.connection.error import NotConnected
from httpy.error import IncompleteRead
from ...curl.error import FailedStatus
from ..error import DownloadedContentMismatch


class ChunksDownloadMismatch(DownloadedContentMismatch):
    def __init__(self, request, chunks):
        super(ChunksDownloadMismatch, self).__init__(request, request.path, chunks.received, chunks.size)


class FailedChunks(FailedStatus):
    def __init__(self, request, status, *args, **kwargs):
        super(FailedChunks, self).__init__(request, status, *args, **kwargs)
        self.message = '\n'.join('%s: %s' % (chunk.id, chunk.error) for chunk in status.failed)

    @property
    def available(self):
        return [request for request in self.failed if not (request.is_write_error() or request.is_not_found())]

    def disconnected(self):
        return any((isinstance(request.error, NotConnected) for request in self.failed))

    def incomplete_read(self):
        return any((isinstance(request.error, IncompleteRead) for request in self.failed))

    def __str__(self):
        return self.message


class FallbackToSingleConnection(FailedChunks):
    def __init__(self, request, status, *args, **kwargs):
        super(FallbackToSingleConnection, self).__init__(request, status, *args, **kwargs)
        errors = super(FallbackToSingleConnection, self).message
        self.message = 'Download chunks failed, fallback to single connection | %s' % errors


class MaxAttemptsReached(FailedStatus):
    pass