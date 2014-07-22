#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os import remove
from os.path import dirname
from shutil import move
from logging import getLogger

from .chunks import Chunks
from pycurwa.download.chunks.download import ChunksDownload, _check_chunks_done
from pycurwa.download.chunks.request import HTTPChunk, FirstChunk
from .stats import DownloadStats
from ..error import Abort, UnexpectedChunkContent, PyCurlError
from ..util import fs_encode, save_join


class HTTPDownload(object):
    '''loads a url http + ftp'''

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

        self.log = getLogger('log')

        self.size = 0

        self.chunk_support = False

    def download(self, chunks=1, resume=False):
        ''' returns new filename or None '''
        chunks = max(1, chunks)

        try:
            statistics = self._download(chunks, resume)
        except PyCurlError, e:
            #code 33 - no resume
            code = e.args[0]
            if code == 33:
                # try again without resume
                self.log.debug('Errno 33 -> Restart without resume')
                statistics = self._download(chunks, False)
            else:
                raise

        return statistics

    def _download(self, chunks_number, resume):
        download = ChunksDownload(self.file_path, self, chunks_number, resume)

        try:
            download.create_chunks()

            statistics = DownloadStats(self.file_path, self.size, download.chunks)

            for time_checked in download.download_checks():
                statistics.update_progress(time_checked, refresh_rate=1)

                if self.abort:
                    raise Abort()

            if not statistics.is_completed():
                raise Exception('Not Completed')

            print 'Saving: ', download.chunks, download.done
            statistics.file_path = self._save_chunks(download, self.file_path)

            return statistics
        finally:
            download.close()

    def _save_chunks(self, download, file_name):
        # make sure downloads are written to disk
        for chunk in download.chunks:
            chunk.flush_file()

        first_chunk = self._copy_chunks(download.info)
        if self.disposition_name and self._use_disposition:
            file_name = save_join(dirname(file_name), self.disposition_name)

        move(first_chunk, fs_encode(file_name))
        download.info.remove()
        return file_name

    def _copy_chunks(self, info):
        first_chunk_path = fs_encode(info.get_chunk_name(0))

        if info.get_count() > 1:
            with open(first_chunk_path, 'rb+') as fo:
                try:
                    for i in range(1, info.get_count()):
                        self._copy_chunk(info, i, fo)
                except UnexpectedChunkContent:
                    remove(first_chunk_path)
                    #there are probably invalid chunks
                    info.remove()

        return first_chunk_path

    #copy in chunks, consumes less memory
    def _copy_chunk(self, info, chunk_number, fo, buf_size=32 * 1024):
        # input file
        #seek to beginning of chunk, to get rid of overlapping chunks
        fo.seek(info.get_chunk_range(chunk_number - 1)[1] + 1)

        chunk_name = fs_encode('%s.chunk%d' % (self.file_path, chunk_number))

        with open(chunk_name, 'rb') as fi:
            while True:
                data = fi.read(buf_size)
                if not data:
                    break
                fo.write(data)

        if fo.tell() < info.get_chunk_range(chunk_number)[1]:
            raise UnexpectedChunkContent()

        remove(chunk_name)