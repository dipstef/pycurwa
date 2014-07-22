import codecs
import os

from unicoder import to_unicode

from ..error import WrongFormat
from ..util import fs_encode


class Chunks(object):
    def __init__(self, name, size=0, resume=False, existing=False):
        #add url
        self.name = to_unicode(name)
        self.size = size
        self.resume = resume
        self.existing = existing
        self.chunks = []

    def set_size(self, size):
        self.size = int(size)

    def add_chunk(self, name, range):
        self.chunks.append((name, range))

    def clear(self):
        self.chunks = []

    def create_chunks(self, chunks):
        self.clear()
        chunk_size = self.size / chunks

        current = 0
        for i in range(chunks):
            end = self.size - 1 if (i == chunks - 1) else current + chunk_size

            self.add_chunk('%s.chunk%s' % (self.name, i), (current, end))

            current += chunk_size + 1

    def save(self):
        fs_name = fs_encode('%s.chunks' % self.name)

        with codecs.open(fs_name, 'w', 'utf_8') as chunks_file:
            chunks_file.write('name:%s\n' % self.name)
            chunks_file.write('size:%s\n' % self.size)

            for i, c in enumerate(self.chunks):
                chunks_file.write('#%d:\n' % i)
                chunks_file.write('\tname:%s\n' % c[0])
                chunks_file.write('\trange:%i-%i\n' % c[1])


    @staticmethod
    def load(name, resume=False):
        fs_name = fs_encode('%s.chunks' % name)

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

    def remove(self):
        fs_name = fs_encode('%s.chunks' % self.name)
        if os.path.exists(fs_name):
            os.remove(fs_name)

    def get_count(self):
        return len(self.chunks)

    def get_chunk_name(self, index):
        return self.chunks[index][0]

    def get_chunk_range(self, index):
        return self.chunks[index][1]

    def __repr__(self):
        ret = 'ChunkInfo: %s, %s\n' % (self.name, self.size)
        for i, c in enumerate(self.chunks):
            ret += '%s# %s\n' % (i, c[1])

        return ret