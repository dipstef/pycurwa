from ...error import DownloadedContentMismatch, FailedStatus


class ChunksDownloadMismatch(DownloadedContentMismatch):
    def __init__(self, downloads):
        super(ChunksDownloadMismatch, self).__init__(downloads.path, downloads.size, downloads.received)


class FailedChunks(FailedStatus):

    def __init__(self, status):
        super(FailedChunks, self).__init__(status)
        self.status = status
        self.message = '\n'.join('%s: %s' % (chunk_id, chunk.error) for chunk_id, chunk in status.failed.iteritems())