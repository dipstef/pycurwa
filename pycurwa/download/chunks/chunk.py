from collections import namedtuple
import os
from ...util import fs_encode


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


class ChunkFileSave(Chunk):

    @property
    def current_size(self):
        return os.path.getsize(self.path)

    def is_completed(self):
        return self.current_size == self.size


class ChunkFileResume(ChunkFileSave):
    pass


class ChunkFile(ChunkFileSave):

    def __new__(cls, path, start, end, resume=False):
        if resume and os.path.exists(path):
            return ChunkFileResume(path, start, end)
        return ChunkFileSave(path, start, end)


class Range(namedtuple('Range', ['start', 'end'])):
    def __new__(cls, start, end):
        assert start < end
        return super(Range, cls).__new__(cls, start, end)

    @property
    def size(self):
        return (self.end - self.start) + 1