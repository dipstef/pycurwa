import codecs
from collections import OrderedDict
import json
import os
import shutil

from unicoder import to_unicode, encoded

from ...error import UnexpectedCopyChunk, UnexpectedContent
from ..files.util import fs_encode


class Chunks(object):
    def __init__(self, file_path, chunks):
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
        json_dict['number'] = len(self._chunks)

        chunks = []

        for chunk in self._chunks:
            chunk_dict = OrderedDict()
            chunk_dict['number'] = chunk.number
            chunk_dict['path'] = chunk.path
            chunk_dict['size'] = chunk.size
            chunk_dict['range'] = [chunk.start, chunk.end]
            chunks.append(chunk_dict)

        json_dict['chunks'] = chunks

        return json_dict

    @property
    def count(self):
        return len(self._chunks)

    def get_chunk(self, index):
        return self._chunks[index]

    def get_chunk_range(self, index):
        return self.get_chunk(index).range

    def __len__(self):
        return len(self._chunks)

    def __iter__(self):
        return iter(self._chunks)

    def __getitem__(self, chunk_number):
        return self._chunks[chunk_number]


def _chunks_file(path):
    return '%s.chunks' % path


def chunks_file_path(path):
    return fs_encode(_chunks_file(path))


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

    def remove(self, all=True):
        _remove(self.path_encoded)
        if all:
            for chunk in self.chunks:
                _remove(chunk.path)

    def __str__(self):
        ret = 'File: %s, %d chunks: \n' % (encoded(self.file_path), self.size)
        for i, chunk in enumerate(self._chunks):
            ret += '%s# %s\n' % (i, chunk)

        return ret


def _remove(path):
        try:
            os.remove(path)
        except OSError:
            # Already removed
            pass


class DownloadChunks(ChunksFile):

    def __init__(self, url, file_path, expected_size, chunks, resume=False):
        self.url = url
        assert expected_size
        self._expected_size = expected_size
        super(DownloadChunks, self).__init__(file_path, chunks)
        self.resume = resume

    @property
    def size(self):
        return self._expected_size

    @property
    def chunks_size(self):
        return super(DownloadChunks, self).size

    def remaining(self):
        return [chunk for chunk in self.chunks if not chunk.is_completed()]

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
        json_dict.update(super(DownloadChunks, self)._json_dict())
        return json_dict

    def copy_chunks(self):
        first_chunk = self[0]

        _ensure_chunk_sizes(self._chunks)

        if self.count > 1:
            self._merge_to_first_chunk(first_chunk)

        shutil.move(first_chunk.path, fs_encode(self.file_path))
        _remove(self.path_encoded)

    def _merge_to_first_chunk(self, first_chunk):
        with open(first_chunk.path, 'rb+') as fo:
            for i in range(1, self.count):
                fo.seek(self[i - 1].range.end + 1)
                _copy_chunk(self[i], fo)

        path_size = first_chunk.get_size()

        if not path_size == self.size:
            self.remove()
            raise UnexpectedCopyChunk(first_chunk.path, path_size, self.size)


def _ensure_chunk_sizes(chunks):
    for chunk in chunks:
        chunk_size = chunk.get_size()

        if chunk_size != chunk.size:
            raise UnexpectedContent(chunk.path, chunk_size, chunk.size)


def _copy_chunk(chunk, first_chunk, buf_size=32 * 1024):
    with open(chunk.path, 'rb') as fi:
        while True:
            data = fi.read(buf_size)
            if not data:
                break
            first_chunk.write(data)

    _remove(chunk.path)


class ChunksDict(OrderedDict):
    def __init__(self, chunks=()):
        super(ChunksDict, self).__init__(((chunk.id, chunk) for chunk in chunks))