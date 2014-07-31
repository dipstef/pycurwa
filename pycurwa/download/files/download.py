import codecs
import json
from . import DownloadChunks, chunks_file_path
from .chunk import ChunkFile


class ExistingDownload(DownloadChunks):

    def __init__(self, url, file_path, resume=False):
        chunks_file = chunks_file_path(file_path)

        with codecs.open(chunks_file, 'r', 'utf-8') as fh:
            json_dict = json.load(fh)

        assert url == json_dict['url']
        expected_size = json_dict['size']
        total = json_dict['number']
        chunks_list = json_dict['chunks']

        chunks = []
        for chunk_dict in chunks_list:
            chunk_file = ChunkFile(chunk_dict['number'], total, chunk_dict['path'], chunk_dict['range'], resume)
            chunks.append(chunk_file)

        super(ExistingDownload, self).__init__(url, file_path, expected_size, chunks, resume)


class NewChunks(DownloadChunks):

    def __init__(self, url, file_path, expected_size, chunks_number, resume=False):
        super(NewChunks, self).__init__(url, file_path, expected_size, chunks=[], resume=resume)
        self._create_chunks(chunks_number)
        self.save()

    def _create_chunks(self, chunks_number):
        chunk_size = self.size / chunks_number
        total = chunks_number - 1

        current = 0
        for number in range(chunks_number):
            end = self.size - 1 if number == total else current + chunk_size

            path = '%s.chunk%s' % (self.file_path, number)
            self._chunks.append(ChunkFile(number+1, chunks_number, path, (current, end)))

            current += chunk_size + 1


class OneChunk(NewChunks):
    def __init__(self, url, file_path, expected_size, resume=False):
        super(OneChunk, self).__init__(url, file_path, expected_size, chunks_number=1, resume=resume)