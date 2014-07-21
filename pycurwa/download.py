#!/usr/bin/env python
# -*- coding: utf-8 -*-
from os import remove, fsync
from os.path import dirname
from time import sleep, time
from shutil import move
from logging import getLogger

import pycurl
from chunks import ChunkInfo, HTTPChunk, UnexpectedChunkContent
from error import Abort, BadHeader
from requests import Bucket
from util import fs_encode, save_join


class ChunksDownload(object):

    def __init__(self, file_name, resume, download, curl_multi, chunks_info):
        self.chunks = []

        self.file_name = file_name
        self._resume = resume

        self._curl_multi = curl_multi
        self._download = download

        self._chunks_info = chunks_info

        # This is a resume, if we were chunked originally assume still can
        if chunks_info.get_count() > 1:
            self._download.chunk_support = True

        self.initial_chunk = None
        self._create_initial_chunk(resume)

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

    def create_chunks(self, chunks_number, resume):
        if not resume:
            self._chunks_info.set_size(self._download.size)
            self._chunks_info.create_chunks(chunks_number)
            self._chunks_info.save()

        chunks_number = self._chunks_info.get_count()
        self.initial_chunk.set_range(self._chunks_info.get_chunk_range(0))

        self._create_chunks(chunks_number)
        self._chunks_created = True

    def _create_chunks(self, chunks_number):
        for i in range(1, chunks_number):
            chunk = HTTPChunk(i, self._download, self._chunks_info.get_chunk_range(i), self._resume)
            handle = chunk.get_handle()

            if handle:
                self._add_chunk(chunk, handle=handle)
            else:
                # close immediatly
                self.log.debug("Invalid curl handle -> closed")
                chunk.close()

    def _create_initial_chunk(self, resume):
        initial_chunk = HTTPChunk(0, self._download, None, resume)
        self.initial_chunk = initial_chunk

        self._add_chunk(initial_chunk)

    def _add_chunk(self, chunk, handle=None):
        self.chunks.append(chunk)
        self._curl_multi.add_handle(handle or chunk.get_handle())

    def chunks_can_be_created(self):
        return not self._chunks_created and self._chunks_supported() and self._download.size

    def _chunks_supported(self):
        return self._download.chunk_support

    def perform(self):
        while True:
            ret, num_handles = self._curl_multi.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

    @property
    def size(self):
        return self._download.size


class HTTPDownload():
    """ loads a url http + ftp """

    def __init__(self, url, filename, get={}, post={}, referer=None, cj=None, bucket=None,
                 options=None, progress_notify=None, disposition=False):
        self.url = url
        self.filename = filename  #complete file destination, not only name
        self.get = get
        self.post = post
        self.referer = referer
        self.cj = cj  #cookiejar if cookies are needed
        self.bucket = bucket
        self.options = options or {}
        self.disposition = disposition
        # all arguments

        self.abort = False
        self.disposition_name = None #will be parsed from content disposition

        self.chunks = []

        self.log = getLogger("log")

        try:
            self.info = ChunkInfo.load(filename)
            self.info.resume = True #resume is only possible with valid info file
            self.infoSaved = True
        except IOError, e:
            self.info = ChunkInfo(filename)

        self.size = self.info.size

        self.chunk_support = None

        self.m = pycurl.CurlMulti()

        #needed for speed calculation
        self._last_arrived = []
        self._speeds = []
        self._last_speeds = [0, 0]

        self._progress_notify = progress_notify

    @property
    def speed(self):
        last = [sum(x) for x in self._last_speeds if x]
        return (sum(self._speeds) + sum(last)) / (1 + len(last))

    @property
    def arrived(self):
        return sum([c.arrived for c in self.chunks])

    @property
    def percent(self):
        if not self.size:
            return 0
        return (self.arrived * 100) / self.size

    def _copy_chunks_to_file(self, chunks):
        # make sure downloads are written to disk
        for chunk in chunks:
            chunk.flush_file()
        self._copy_chunks()

    def _copy_chunks(self):
        init = fs_encode(self.info.get_chunk_name(0)) #initial chunk name

        if self.info.get_count() > 1:
            with open(init, "rb+") as fo:
                try:
                    for i in range(1, self.info.get_count()):
                        self._copy_chunk(i, fo)
                except UnexpectedChunkContent:
                    remove(init)
                    self.info.remove() #there are probably invalid chunks

        if self.disposition_name and self.disposition:
            self.filename = save_join(dirname(self.filename), self.disposition_name)

        move(init, fs_encode(self.filename))
        self.info.remove() #remove info file

    #copy in chunks, consumes less memory
    def _copy_chunk(self, chunk_number, fo, buf_size=32 * 1024):
        # input file
        #seek to beginning of chunk, to get rid of overlapping chunks
        fo.seek(self.info.get_chunk_range(chunk_number - 1)[1] + 1)
        chunk_name = fs_encode("%s.chunk%d" % (self.filename, chunk_number))

        with open(chunk_name, "rb") as fi:
            while True:
                data = fi.read(buf_size)
                if not data:
                    break
                fo.write(data)

        if fo.tell() < self.info.get_chunk_range(chunk_number)[1]:
            raise UnexpectedChunkContent()

        remove(chunk_name)

    def download(self, chunks=1, resume=False):
        """ returns new filename or None """

        chunks = max(1, chunks)

        resume = self.info.resume and resume

        try:
            self._download(chunks, resume)
        except pycurl.error, e:
            #code 33 - no resume
            code = e.args[0]
            if code == 33:
                # try again without resume
                self.log.debug("Errno 33 -> Restart without resume")

                #remove old handles
                for chunk in self.chunks:
                    self._close_chunk(chunk)

                return self._download(chunks, False)
            else:
                raise
        finally:
            self.close()

        if self.disposition_name and self.disposition:
            return self.disposition_name
        return None

    def _download(self, chunks_number, resume):
        if not resume:
            self.info.clear()
            self.info.add_chunk("%s.chunk0" % self.filename, (0, 0)) #create an initial entry

        last_time_check = 0

        chunks_download = ChunksDownload(self.filename, resume, self, self.m, self.info)
        self.chunks = chunks_download.chunks

        while not chunks_download.done:
            #need to create chunks
            if chunks_download.chunks_can_be_created():
                chunks_download.create_chunks(chunks_number, resume)

            chunks_download.perform()

            now = time()

            self._check_chunks_done(now, chunks_download)

            if not chunks_download.done:
                # calc speed once per second, averaging over 3 seconds
                if last_time_check + 1 < now:
                    self._update_progress(last_time_check, now)

                    last_time_check = now

                    if self._progress_notify:
                        self._progress_notify(self.percent)

                if self.abort:
                    raise Abort()

                #sleep(0.003) #supress busy waiting - limits dl speed to  (1 / x) * buffersize
                self.m.select(1)

        self._copy_chunks_to_file(chunks_download.chunks)

    def _update_progress(self, last_time_check, now):
        diff = [c.arrived - (self._last_arrived[i] if len(self._last_arrived) > i else 0) for i, c in enumerate(self.chunks)]

        self._last_speeds[1] = self._last_speeds[0]
        self._last_speeds[0] = self._speeds
        self._speeds = [float(a) / (now - last_time_check) for a in diff]
        self._last_arrived = [c.arrived for c in self.chunks]

    def _check_chunks_done(self, now, chunks_download):
        initial_chunk = chunks_download.initial_chunk
        chunks_completed = chunks_download.chunks_completed

        # reduce these calls
        while chunks_download.checked_less_than(now, seconds=0.5):
            # list of failed curl handles
            failed, completed, handles_remaining = self._split_done_and_failed(self.m)

            chunks_download.add_chunks_completed(completed)

            for chunk, error in failed:
                self.log.debug("Chunk %d failed: %s" % (chunk.id + 1, str(error)))

            if not handles_remaining:  # no more infos to get
                # check if init is not finished so we reset download connections
                # note that other chunks are closed and downloaded with init too
                if failed:
                    chunks_failed = [chunk for chunk, error in failed]
                    ex = failed[-1][1]

                    if initial_chunk not in chunks_failed and initial_chunk.c not in chunks_completed:
                        self.log.error(("Download chunks failed, fallback to single connection | %s" % (str(ex))))

                        self._revert_to_single_connection(initial_chunk)
                    else:
                        raise ex

                chunks_download.last_check = now

                if len(chunks_completed) >= len(chunks_download.chunks):
                    if len(chunks_completed) > len(chunks_download.chunks):
                        self.log.warning("Finished download chunks size incorrect, please report bug.")

                    chunks_download.completed()

                break

    def _split_done_and_failed(self, curl_multi):
        chunks_failed, chunks_completed = [], set()

        num_q, ok_list, err_list = curl_multi.info_read()

        for c in ok_list:
            chunk = self._find_handle_chunk(c)
            try:  # check if the header implies success, else add it to failed list
                chunk.verify_header()
            except BadHeader, e:
                chunks_failed.append((chunk, e))
            else:
                chunks_completed.add(c)

        for c in err_list:
            curl, errno, msg = c
            chunk = self._find_handle_chunk(curl)
            # test if chunk was finished
            if errno != 23 or "0 !=" not in msg:
                chunks_failed.append((chunk, pycurl.error(errno, msg)))
            else:
                try:  # check if the header implies success, else add it to failed list
                    chunk.verify_header()
                except BadHeader, e:
                    chunks_failed.append((chunk, e))
                else:
                    chunks_completed.add(curl)

        return chunks_failed, chunks_completed, num_q

    def _revert_to_single_connection(self, initial_chunk):
        # list of chunks to clean and remove
        to_clean = filter(lambda x: x is not initial_chunk, self.chunks)
        for chunk in to_clean:
            self._close_chunk(chunk)
            self.chunks.remove(chunk)
            chunk_name = fs_encode(self.info.get_chunk_name(chunk.id))
            remove(chunk_name)

        #let first chunk load the rest and update the info file
        initial_chunk.reset_range()
        self.info.clear()
        self.info.add_chunk("%s.chunk0" % self.filename, (0, self.size))
        self.info.save()

    def _find_handle_chunk(self, handle):
        """ linear search to find a chunk (should be ok since chunk size is usually low) """
        for chunk in self.chunks:
            if chunk.c == handle:
                return chunk

    def _close_chunk(self, chunk):
        try:
            self.m.remove_handle(chunk.c)
        except pycurl.error, e:
            self.log.debug("Error removing chunk: %s" % str(e))
        finally:
            chunk.close()

    def close(self):
        """ cleanup """
        for chunk in self.chunks:
            self._close_chunk(chunk)

        self.chunks = []
        if hasattr(self, "m"):
            self.m.close()
            del self.m
        if hasattr(self, "cj"):
            del self.cj
        if hasattr(self, "info"):
            del self.info


def main():
    import os
    # url = "http://speedtest.netcologne.de/test_100mb.bin"
    url = "http://download.thinkbroadband.com/10MB.zip"
    file_name = os.path.basename(url)

    bucket = Bucket()
    bucket.set_max_speed(200 * 1024)
    #bucket = None
    print "starting"
    d = HTTPDownload(url, file_name, bucket=bucket)
    d.download(chunks=3, resume=True)
    print d.speed


if __name__ == "__main__":
    main()