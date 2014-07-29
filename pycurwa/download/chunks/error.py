from pycurwa.error import DownloadedContentMismatch


class ChunksDownloadMismatch(DownloadedContentMismatch):
    def __init__(self, chunks_file, received):
        super(ChunksDownloadMismatch, self).__init__(chunks_file.file_path, chunks_file.size, received)