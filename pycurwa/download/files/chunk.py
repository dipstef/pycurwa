from collections import namedtuple
import os

from .util import fs_encode


class Chunk(namedtuple('Chunk', ['number', 'chunks', 'path', 'range'])):

    def __new__(cls, number, chunks, path, bytes_range):
        assert number
        assert number <= chunks
        return super(Chunk, cls).__new__(cls, number, chunks, fs_encode(path), Range(*bytes_range))

    def is_last(self):
        return self.number == self.chunks

    @property
    def id(self):
        return self.number - 1

    @property
    def size(self):
        return self.range.size

    @property
    def start(self):
        return self.range.start

    @property
    def end(self):
        return self.range.end

    @property
    def download_range(self):
        return self.range if not self.is_last() else Range(self.start, None)


class ChunkFileSave(Chunk):
    resume = False

    def is_completed(self):
        try:
            return self.get_size() >= self.size
        except OSError:
            return False

    def get_size(self):
        return os.path.getsize(self.path)


class ChunkFileResume(ChunkFileSave):
    resume = True


class ChunkFile(ChunkFileSave):

    def __new__(cls, number, chunks, path, bytes_range, resume=False):
        if resume and os.path.exists(path):
            return ChunkFileResume(number, chunks, path, bytes_range)

        return ChunkFileSave(number, chunks, path, bytes_range)


class Range(namedtuple('Range', ['start', 'end'])):

    def __new__(cls, start, end):
        return super(Range, cls).__new__(cls, start, end)

    @property
    def size(self):
        return (self.end - self.start) + 1 if self.end else None