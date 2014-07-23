# -*- coding: utf-8 -*-
from os import remove
from os.path import dirname
from shutil import move

from procol.console import print_err

from .chunks import Chunks
from .chunks.download import ChunksDownload
from .chunks.request import HTTPChunk, FirstChunk
from .stats import DownloadStats
from ..error import Abort, UnexpectedChunkContent, PyCurlError
from ..util import fs_encode, save_join


class HTTPDownload(object):

    def __init__(self, url, filename, get=None, post=None, referrer=None, cj=None, bucket=None,
                 options=None, progress_notify=None, use_disposition=False):
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

        try:
            statistics = DownloadStats(self.file_path, self.size, download.chunks)

            for time_checked in download.download_checks():
                statistics.update_progress(time_checked, refresh_rate=1)

                if self.abort:
                    raise Abort()

            if not download.is_completed():
                raise Exception('Not Completed')

            statistics.file_path = self._save_chunks(download, self.file_path)

            return statistics
        finally:
            download.close()

    def _save_chunks(self, download, file_name):
        # make sure downloads are written to disk
        for chunk in download.chunks:
            chunk.flush_file()

        first_chunk = _copy_chunks(download.chunks_file)
        if self.disposition_name and self._use_disposition:
            file_name = save_join(dirname(file_name), self.disposition_name)

        move(first_chunk, fs_encode(file_name))
        download.chunks_file.remove()
        return file_name


def _copy_chunks(info):
    first_chunk_path = info[0].path

    if info.count > 1:
        with open(first_chunk_path, 'rb+') as fo:
            try:
                for i in range(1, info.count):
                    fo.seek(info[i - 1].range.end + 1)

                    _copy_chunk(info[i], fo)
            except UnexpectedChunkContent:
                remove(first_chunk_path)
                # there are probably invalid chunks
                info.remove()

    return first_chunk_path


# copy in chunks, consumes less memory
def _copy_chunk(chunk, fo, buf_size=32 * 1024):
    # input file
    # seek to beginning of chunk, to get rid of overlapping chunks
    with open(chunk.path, 'rb') as fi:
        while True:
            data = fi.read(buf_size)
            if not data:
                break
            fo.write(data)

    if fo.tell() < chunk.range.end:
        raise UnexpectedChunkContent()

    remove(chunk.path)