import codecs
from collections import namedtuple
import os

from unicoder import to_unicode, byte_string, encoded

from ..error import WrongFormat
from ..util import fs_encode


class FileChunks(object):

    def __init__(self, file_path, chunks):
        #add url
        self.file_path = to_unicode(file_path)
        self.path = '%s.chunks' % self.file_path

        self._chunks = chunks

    @property
    def size(self):
        return sum([chunk.size for chunk in self._chunks])

    @property
    def chunks(self):
        return list(self._chunks)


    @property
    def path_encoded(self):
        return fs_encode(self.path)

    def __str__(self):
        ret = 'File: %s, %d chunks: \n' % (encoded(self.file_path), self.size)
        for i, chunk in enumerate(self._chunks):
            ret += '%s# %s\n' % (i, chunk)

        return ret


class DownloadChunks(FileChunks):

    def __init__(self, url, file_path, chunks):
        super(DownloadChunks, self).__init__(file_path, chunks)
        self.url = url

    def __str__(self):
        ret = 'Download %s: %s, %d chunks: \n' % (encoded(self.url), encoded(self.file_path), self.size)

        for i, chunk in enumerate(self._chunks):
            ret += '%s# %s\n' % (i, chunk)

        return ret


class Chunks(object):
    def __init__(self, name, size=0, resume=False, existing=False):
        #add url
        self.file_path = to_unicode(name)
        self.path = '%s.chunks' % self.file_path

        self.size = size
        self.resume = resume
        self.existing = existing
        self.chunks = []

    def set_size(self, size):
        self.size = int(size)

    def add_chunk(self, name, byte_range):
        self.chunks.append((name, byte_range))

    def clear(self):
        self.chunks = []

    def create_chunks(self, chunks):
        self.clear()
        chunk_size = self.size / chunks

        current = 0
        for i in range(chunks):
            end = self.size - 1 if (i == chunks - 1) else current + chunk_size

            self.add_chunk('%s.chunk%s' % (self.file_path, i), (current, end))

            current += chunk_size + 1

    def save(self):
        with codecs.open(self.path_encoded, 'w', 'utf_8') as chunks_file:
            chunks_file.write('name:%s\n' % self.file_path)
            chunks_file.write('size:%s\n' % self.size)

            for i, c in enumerate(self.chunks):
                chunks_file.write('#%d:\n' % i)
                chunks_file.write('\tname:%s\n' % c[0])
                chunks_file.write('\trange:%i-%i\n' % c[1])

    def remove(self):
        try:
            os.remove(self.path_encoded)
        except OSError:
            #Already removed
            pass

    def get_count(self):
        return len(self.chunks)

    def get_chunk_name(self, index):
        return self.chunks[index][0]

    def get_chunk_range(self, index):
        return self.chunks[index][1]

    @property
    def path_encoded(self):
        return fs_encode(self.path)

    def __repr__(self):
        ret = 'Chunks File: %s, %s\n' % (self.path, self.size)
        for i, c in enumerate(self.chunks):
            ret += '%s# %s\n' % (i, c[1])

        return ret


class Range(namedtuple('Range', ['start', 'end'])):
    def __new__(cls, start, end):
        assert start < end
        return super(Range, cls).__new__(cls, start, end)

    @property
    def size(self):
        return (self.end - self.start) + 1


class Chunk(namedtuple('Chunk', ['path', 'range'])):

    def __new__(cls, path, start, end):
        return super(Chunk, cls).__new__(cls, fs_encode(path), Range(start, end))

    @property
    def size(self):
        return self.range.size

    @property
    def start(self):
        return self.range.start

    @property
    def end(self):
        return self.range.end


class ChunksFile(object):

    def __new__(cls, file_path, *more):
        return super(ChunksFile, cls).__new__(*more)


class ExistingChunksFile(object):

    def __init__(self):
        super(ExistingChunksFile, self).__init__()


    @staticmethod
    def load(name, resume=False):
        fs_name = fs_encode('%s.chunks' % name)

        #json.loads(ensure_ascii=False)
        with codecs.open(fs_name, 'r', 'utf_8') as fh:

            name = fh.readline()[:-1]
            size = fh.readline()[:-1]

            if name.startswith('name:') and size.startswith('size:'):
                name = name[5:]
                size = int(size[5:])
            else:
                raise WrongFormat()

            chunk_info = Chunks(name, size=size, resume=resume, existing=True)

            while True:
                if not fh.readline():
                    break
                name = fh.readline()[1:-1]
                bytes_range = fh.readline()[1:-1]

                if name.startswith('name:') and bytes_range.startswith('range:'):
                    name = name[5:]
                    bytes_range = bytes_range[6:].split('-')
                else:
                    raise WrongFormat()

                chunk_info.add_chunk(name, (long(bytes_range[0]), long(bytes_range[1])))

            return chunk_info