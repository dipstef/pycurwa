# -*- coding: utf-8 -*-
from os import remove
import os
from os.path import dirname
from shutil import move

from procol.console import print_err

from .chunks import Chunks
from .chunks.download import ChunksDownload
from ..error import UnexpectedContent
from ..curl.error import PyCurlError
from ..util import fs_encode, save_join


class HTTPDownload(object):

    def __init__(self, url, filename, get=None, post=None, referrer=None, cj=None, bucket=None,
                 options=None, use_disposition=False):
        self.url = url
        self.file_path = filename
        self.get = get
        self.post = post
        self.referrer = referrer
        self.cookies = cj
        self.bucket = bucket
        self.options = options or {}

        self._use_disposition = use_disposition
        # all arguments

        self.abort = False
        self.disposition_name = None

        self.size = 0

    def download(self, chunks_number=1, resume=False):
        chunks_number = max(1, chunks_number)

        try:
            statistics = self._download(chunks_number, resume)
        except PyCurlError, e:
            #code 33 - no resume
            code = e.args[0]
            if code == 33:
                print_err('Errno 33 -> Restart without resume')
                statistics = self._download(chunks_number, resume=False)
            else:
                raise

        return statistics

    def _download(self, chunks_number, resume):
        download = ChunksDownload(self.file_path, self, chunks_number, resume)

        statistics = download.perform()

        first_chunk = _copy_chunks(download.chunks_file)

        path_size = os.path.getsize(first_chunk)
        try:
            if not path_size == download.size:
                raise Exception('Not Completed: %d expected %d' % (path_size, download.size))

            statistics.file_path = self._move_to_download_file(first_chunk, download.path)
            return statistics
        finally:
            download.chunks_file.remove()

    def _move_to_download_file(self, first_chunk, file_name):

        if self.disposition_name and self._use_disposition:
            file_name = save_join(dirname(file_name), self.disposition_name)

        move(first_chunk, fs_encode(file_name))

        return file_name


def _copy_chunks(info):
    first_chunk_path = info[0].path

    for chunk in info.chunks:
        chunk_size = os.path.getsize(chunk.path)

        if chunk_size != chunk.size:
        #    raise UnexpectedChunkContent(chunk.path, chunk_size, chunk.size)
            print_err(UnexpectedContent(chunk.path, chunk_size, chunk.size))

    if info.count > 1:
        with open(first_chunk_path, 'rb+') as fo:
            try:
                for i in range(1, info.count):
                    # input file
                    # seek to beginning of chunk, to get rid of overlapping chunks
                    fo.seek(info[i - 1].range.end + 1)

                    _copy_chunk(info[i], fo)
            except UnexpectedContent:
                remove(first_chunk_path)
                # there are probably invalid chunks
                info.remove()
                raise

    return first_chunk_path


# copy in chunks, consumes less memory
def _copy_chunk(chunk, first_chunk, buf_size=32 * 1024):
    with open(chunk.path, 'rb') as fi:
        while True:
            data = fi.read(buf_size)
            if not data:
                break
            first_chunk.write(data)

    remove(chunk.path)