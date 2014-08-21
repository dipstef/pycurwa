from httpy.error import HttpError
from ...error import DownloadedContentMismatch


class UnexpectedCopyChunk(DownloadedContentMismatch):
    def __init__(self, request, path, actual, expected):
        super(UnexpectedCopyChunk, self).__init__(request, path, actual, expected)
        self.message = 'Not Completed %s: %d expected %d' % (path, actual, expected)


class ChunkCreationError(HttpError):
    def __init__(self, request, path):
        super(ChunkCreationError, self).__init__(request, path)
        self.path = path
        self.message = 'Error creating chunks file for download %s, %s' % (path, str(request))


class ChunkCreationException(ChunkCreationError):
    def __init__(self, request, path, error):
        super(ChunkCreationError, self).__init__(request, path)
        self.message = 'Error :%s creating chunks file for download %s, %s' % (str(error), path, str(request))
        self.error = error


class ChunksAlreadyExisting(ChunkCreationError):
    def __init__(self, request, download_path, chunks_file_path, url):
        super(ChunksAlreadyExisting, self).__init__(request, download_path)
        self.message = '%s, Another download exists for the same chunks file: %s : %s' % (str(request),
                                                                                          chunks_file_path, url)