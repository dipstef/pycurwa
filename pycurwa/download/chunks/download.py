import os
import time

from procol.console import print_err

from . import load_chunks, CreateChunksFile, OneChunk, ChunkFile
from .request import HTTPChunk, FirstChunk
from ...curl import CurlMulti, perform_multi, PyCurlError
from ...error import BadHeader


class ChunksDownloading(object):

    def __init__(self, file_path, chunks):
        self.curl = CurlMulti()
        self.file_path = file_path
        self.chunks_file = chunks

        self.chunks_completed = set()
        self.chunks = []

    def download_checks(self):
        while not self.is_done():
            perform_multi(self.curl)

            time_checked = _check_chunks_done(self)

            if not self.is_done():
                yield time_checked

                self.curl.select(1)

    def is_done(self):
        return len(self.chunks_completed) >= len(self.chunks)

    def close(self):
        #remove old handles
        for chunk in self.chunks:
            self._close_chunk(chunk)

    def _close_chunk(self, chunk):
        try:
            self.curl.remove_handle(chunk.curl)
        except PyCurlError, e:
            print_err('Error removing chunk: %s' % str(e))
        finally:
            chunk.close()

    def _remove_chunk(self, chunk):
        self._close_chunk(chunk)
        os.remove(chunk.file_path)

    def is_completed(self):
        chunks_received = sum([c.received for c in self.chunks])
        return self.chunks_file.size == chunks_received


class DownloadChunks(ChunksDownloading):

    def __init__(self, file_path, download, chunks):
        self._download = download

        super(DownloadChunks, self).__init__(file_path, chunks)

        self._chunks_number = chunks.count

        self.last_check = None
        self._add_chunks()

    def checked_less_than(self, now, seconds=0.5):
        return not self.last_check or self.last_check + seconds < now

    def add_chunks_completed(self, completed):
        self.chunks_completed.update(completed)

    def _add_chunks(self):
        for chunk in self.chunks_file:
            http_chunk = HTTPChunk(chunk, self._download)

            self.chunks.append(http_chunk)
            self.curl.add_handle(http_chunk.curl)

    @property
    def size(self):
        return self._download.size

    def revert_to_one_connection(self):
        #it returns only even element when the list is not copied, odd
        for chunk in list(self.chunks):
            self._remove_chunk(chunk)
            self.chunks.remove(chunk)
            assert chunk not in self.chunks

        self.chunks_file = OneChunk(self._download.url, self.file_path, self.size, resume=True)
        self._add_chunks()

    @property
    def initial(self):
        return self.chunks[0]

    def chunk_for_handle(self, handle):
        for chunk in self.chunks:
            if chunk.curl == handle:
                return chunk

    def info_read(self):
        return self.curl.info_read()


class DownloadExistingChunks(DownloadChunks):

    def __init__(self, file_path, download, chunks):
        super(DownloadExistingChunks, self).__init__(file_path, download, chunks)


class DownloadMissingChunks(DownloadChunks):

    def __init__(self, file_path, download, chunks_number):
        download_size = _resolve_size(file_path, download)

        chunks = CreateChunksFile(download.url, file_path, download_size, chunks_number)
        super(DownloadMissingChunks, self).__init__(file_path, download, chunks)


def _resolve_size(file_path, download):
    chunk = ChunkFile(1, 1, '%s.chunk%s' % (file_path, 0), (0, 1024))
    initial = FirstChunk(chunk, download)

    with CurlMulti() as curl:
        curl.add_handle(initial.curl)

        while not download.size:
            curl.perform()
            curl.select(1)

        curl.remove_handle(initial.curl)
        initial.close()

    return download.size


class ChunksDownload(DownloadChunks):

    def __new__(cls, file_path, download, chunks_number, resume):
        try:
            chunks = load_chunks(download.url, file_path, resume)

            download.size = chunks.size

            return DownloadChunks(file_path, download, chunks)
        except IOError, e:
            return DownloadMissingChunks(file_path, download, chunks_number)


def _check_chunks_done(download):
    now = time.time()

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
                ex = failed[-1][1]

                if len(download.chunks) > 1:
                    # 416 Range not satisfiable check
                    print_err(('Download chunks failed, fallback to single connection | %s' % (str(ex))))
                    download.revert_to_one_connection()
                    time.sleep(2)
                else:
                    raise ex

            download.last_check = now

            if len(download.chunks_completed) > len(download.chunks):
                print_err('Finished download chunks size incorrect, please report bug.')

            break

    return now


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
            chunks_failed.append((chunk, PyCurlError(errno, msg)))
        else:
            try:  # check if the header implies success, else add it to failed list
                chunk.verify_header()
            except BadHeader, e:
                chunks_failed.append((chunk, e))
            else:
                chunks_completed.add(curl)

    return chunks_failed, chunks_completed, num_q