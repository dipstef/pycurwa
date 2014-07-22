import codecs
from collections import OrderedDict
import json

from unicoder import to_unicode, encoded

from pycurwa.download.chunks.chunk import Chunk, ChunkFile
from ...util import fs_encode


class Chunks(object):
    def __init__(self, file_path, chunks):
        #add url
        self.file_path = to_unicode(file_path)
        self._chunks = chunks

    @property
    def size(self):
        return sum([chunk.size for chunk in self._chunks])

    @property
    def chunks(self):
        return list(self._chunks)

    def json(self):
        return json.dumps(self._json_dict(), indent=4, encoding='utf-8')

    def _json_dict(self):
        json_dict = OrderedDict()

        json_dict['path'] = self.file_path
        json_dict['size'] = self.size

        chunks = OrderedDict()
        for number, chunk in enumerate(self._chunks):
            chunk_dict = OrderedDict()
            chunk_dict['path'] = chunk.path
            chunk_dict['size'] = chunk.size
            chunk_dict['range'] = [chunk.start, chunk.end]
            chunks[number] = chunk_dict

        json_dict['chunks'] = chunks

        return json_dict

    @property
    def count(self):
        return len(self._chunks)

    def get_chunk(self, index):
        return self._chunks[index]

    def get_chunk_path(self, index):
        return self.get_chunk(index).path

    def get_chunk_range(self, index):
        return self.get_chunk(index).range


def _chunks_file(path):
    return '%s.chunks' % path


class ChunksFile(Chunks):

    def __init__(self, file_path, chunks):
        super(ChunksFile, self).__init__(file_path, chunks)
        self.path = _chunks_file(file_path)

    @property
    def path_encoded(self):
        return fs_encode(self.path)

    def save(self):
        with codecs.open(self.path_encoded, 'w', 'utf-8') as chunks_file:
            return json.dump(self._json_dict(), chunks_file, indent=4, encoding='utf-8')

    def __str__(self):
        ret = 'File: %s, %d chunks: \n' % (encoded(self.file_path), self.size)
        for i, chunk in enumerate(self._chunks):
            ret += '%s# %s\n' % (i, chunk)

        return ret


class DownloadChunksFile(ChunksFile):

    def __init__(self, url, file_path, expected_size, chunks, resume=False):
        self.url = url
        assert expected_size
        self._expected_size = expected_size
        super(DownloadChunksFile, self).__init__(file_path, chunks)
        self.resume = resume

    @property
    def size(self):
        return self._expected_size

    @property
    def chunks_size(self):
        return super(DownloadChunksFile, self).size

    def is_completed(self):
        return self._expected_size == self.chunks_size

    def __str__(self):
        ret = 'Download %s: %s, %d chunks: \n' % (encoded(self.url), encoded(self.file_path), self.size)

        for i, chunk in enumerate(self._chunks):
            ret += '%s# %s\n' % (i, chunk)

        return ret

    def _json_dict(self):
        json_dict = OrderedDict()
        json_dict['url'] = self.url
        json_dict.update(super(DownloadChunksFile, self)._json_dict())
        return json_dict


class ExistingDownloadChunks(DownloadChunksFile):
    def __init__(self, url, file_path, resume=False):
        chunks_file = fs_encode(_chunks_file(file_path))

        with codecs.open(chunks_file, 'r', 'utf-8') as fh:
            json_dict = json.load(fh)

        assert url == json_dict['url']
        expected_size = json_dict['size']
        chunks_dict = json_dict['chunks']

        chunks = []
        for chunk_dict in chunks_dict.values():
            chunk_file = ChunkFile(chunk_dict['path'], chunk_dict['range'][0], chunk_dict['range'][1], resume)
            chunks.append(chunk_file)

        super(ExistingDownloadChunks, self).__init__(url, file_path, expected_size, chunks, resume)


class CreateChunksFile(DownloadChunksFile):

    def __init__(self, url, file_path, expected_size, chunks_number):
        super(CreateChunksFile, self).__init__(url, file_path, expected_size, chunks=[])
        self._create_chunks(chunks_number)
        self.save()

    def _create_chunks(self, chunks_number):
        chunk_size = self.size / chunks_number

        current = 0
        for i in range(chunks_number):
            end = self.size - 1 if (i == chunks_number - 1) else current + chunk_size
            self._add_chunk(i, (current, end))

            current += chunk_size + 1

    def _add_chunk(self, number, bytes_range):
        path = '%s.chunk%s' % (self.file_path, number)

        self._chunks.append(Chunk(path, bytes_range[0], bytes_range[1]))


class OneChunk(CreateChunksFile):
    def __init__(self, url, file_path, expected_size):
        super(OneChunk, self).__init__(url, file_path, expected_size, chunks_number=1)


def load_chunks(url, file_path, resume=False):
    return ExistingDownloadChunks(url, resume, file_path)