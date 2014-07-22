#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os import remove
from os.path import dirname
from time import time
from shutil import move
from logging import getLogger
from procol.console import print_err

import pycurl

from .chunks import Chunks
from .request import HTTPChunk, FirstChunk
from .stats import DownloadStats

from ..error import Abort, BadHeader, UnexpectedChunkContent
from ..util import fs_encode, save_join


class ChunksDownload(object):

    def __init__(self, file_path, download, chunks_number=1, resume=False):
        self.chunks = []

        self.file_path = file_path

        self.curl = pycurl.CurlMulti()

        self._download = download

        chunks_info = _load_chunks_info(self.file_path, resume)

        self.info = chunks_info
        self._chunks_number = chunks_number if not chunks_info.existing else chunks_info.get_count()

        download.size = self.info.size
        #if we have already chunks we assume downloads supports chunks
        download.chunk_support = chunks_info.existing

        self.initial = self._create_initial_chunk()

        self._chunks_created = False
        self.last_check = None
        self.done = False
        self.chunks_completed = set()
        self.log = download.log

    def checked_less_than(self, now, seconds=0.5):
        return not self.last_check or self.last_check + seconds < now

    def completed(self):
        self.done = True

    def add_chunks_completed(self, completed):
        self.chunks_completed.update(completed)

    def create_chunks(self):
        while not self._chunks_can_be_created():
            self.curl.perform()
            self.curl.select(1)

        self._create_chunks()

    def _create_chunks(self):
        if not self.info.resume:
            self.info.set_size(self._download.size)
            self.info.create_chunks(self._chunks_number)
            self.info.save()

        chunks_number = self.info.get_count()
        self.initial.set_range(self.info.get_chunk_range(0))
        self._add_chunks(chunks_number)
        self._chunks_created = True

    def _add_chunks(self, chunks_number):
        for i in range(1, chunks_number):
            chunk = HTTPChunk(i, self._download, self.info, self.info.get_chunk_range(i))

            self._add_chunk(chunk)

    def _create_initial_chunk(self):
        initial_chunk = FirstChunk(self._download, self.info)

        self._add_chunk(initial_chunk)

        return initial_chunk

    def _add_chunk(self, chunk, handle=None):
        self.chunks.append(chunk)
        self.curl.add_handle(handle or chunk.curl)

    def _chunks_can_be_created(self):
        return not self._chunks_created and self._download.chunk_support and self.size

    def perform(self):
        while True:
            ret, num_handles = self.curl.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

    @property
    def size(self):
        return self._download.size

    def close(self):
        #remove old handles
        for chunk in self.chunks:
            self._close_chunk(chunk)

    def _close_chunk(self, chunk):
        try:
            self.curl.remove_handle(chunk.curl)
        except pycurl.error, e:
            print_err('Error removing chunk: %s' % str(e))
        finally:
            chunk.close()

    def revert_to_one_connection(self):
        # list of chunks to clean and remove
        to_clean = filter(lambda x: x is not self.initial, self.chunks)

        for chunk in to_clean:
            self._remove(chunk)

        #let first chunk load the rest and update the info file
        self.initial.reset_range()
        self.info.clear()
        self.info.add_chunk('%s.chunk0' % self.file_path, (0, self.size))
        self.info.save()

    def _remove(self, chunk):
        self._close_chunk(chunk)

        self.chunks.remove(chunk)

        chunk_name = fs_encode(self.info.get_chunk_name(chunk.id))
        remove(chunk_name)

    def chunk_for_handle(self, handle):
        for chunk in self.chunks:
            if chunk.curl == handle:
                return chunk

    def info_read(self):
        return self.curl.info_read()


def _load_chunks_info(file_path, resume):
    info = _load_chunks_resume_info(file_path) if resume else Chunks(file_path)
    if not info.resume:
        info = Chunks(file_path)
        info.add_chunk('%s.chunk0' % file_path, (0, 0))
    return info


def _load_chunks_resume_info(file_path):
    try:
        info = Chunks.load(file_path, resume=True)
        info.resume = True  # resume is only possible with valid info file
    except IOError, e:
        info = Chunks(file_path)
    return info


class HTTPDownload(object):
    '''loads a url http + ftp'''

    def __init__(self, url, filename, get={}, post={}, referrer=None, cj=None, bucket=None,
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
            stats = self._download(chunks, resume)
        except pycurl.error, e:
            #code 33 - no resume
            code = e.args[0]
            if code == 33:
                # try again without resume
                self.log.debug('Errno 33 -> Restart without resume')
                stats = self._download(chunks, False)
            else:
                raise

        return stats

    def _download(self, chunks_number, resume):
        download = ChunksDownload(self.file_path, self, chunks_number, resume)

        try:
            download.create_chunks()

            stats = DownloadStats(self.file_path, self.size, download.chunks)

            while not download.done:
                download.perform()

                now = time()
                _check_chunks_done(now, download)

                if not download.done:
                    # calc speed once per second, averaging over 3 seconds
                    if stats.refresh_speed(now, seconds=1):
                        stats.update_progress(now)

                    if self.abort:
                        raise Abort()

                    #sleep(0.003) #supress busy waiting - limits dl speed to  (1 / x) * buffersize
                    download.curl.select(1)

            if not stats.is_completed():
                raise Exception('Not Completed')

            print 'Saving: ', download.chunks, download.done
            stats.file_path = self._save_chunks(download, self.file_path)

            return stats
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
        download.info._remove()
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
                    info._remove()

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


def _check_chunks_done(now, download):
    initial_chunk = download.initial
    chunks_completed = download.chunks_completed

    # reduce these calls
    while download.checked_less_than(now, seconds=0.5):
        # list of failed curl handles
        failed, completed, handles_remaining = _split_done_and_failed(download)

        download.add_chunks_completed(completed)

        for chunk, error in failed:
            print_err('Chunk %d failed: %s' % (chunk.id + 1, str(error)))

        if not handles_remaining:  # no more infos to get
            # check if init is not finished so we reset download connections
            # note that other chunks are closed and downloaded with init too
            if failed:
                chunks_failed = [chunk for chunk, error in failed]
                ex = failed[-1][1]

                if initial_chunk not in chunks_failed and initial_chunk.curl not in chunks_completed:
                    # 416 Range not satisfiable check
                    print_err(('Download chunks failed, fallback to single connection | %s' % (str(ex))))

                    download.revert_to_one_connection()
                else:
                    raise ex

            download.last_check = now

            if len(chunks_completed) >= len(download.chunks):
                if len(chunks_completed) > len(download.chunks):
                    print_err('Finished download chunks size incorrect, please report bug.')

                download.completed()

            break


def _split_done_and_failed(download):
    chunks_failed, chunks_completed = [], set()

    num_q, ok_list, err_list = download.info_read()

    for curl in ok_list:
        chunk = download.chunk_for_handle(curl)
        try:  # check if the header implies success, else add it to failed list
            chunk.verify_header()
        except BadHeader, e:
            chunks_failed.append((chunk, e))
        else:
            chunks_completed.add(curl)

    for curl in err_list:
        curl, errno, msg = curl
        chunk = download.chunk_for_handle(curl)

        # test if chunk was finished
        if errno != 23 or '0 !=' not in msg:
            chunks_failed.append((chunk, pycurl.error(errno, msg)))
        else:
            try:  # check if the header implies success, else add it to failed list
                chunk.verify_header()
            except BadHeader, e:
                chunks_failed.append((chunk, e))
            else:
                chunks_completed.add(curl)

    return chunks_failed, chunks_completed, num_q