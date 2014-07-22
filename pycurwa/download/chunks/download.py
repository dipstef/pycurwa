from os import remove
from time import time

from procol.console import print_err

from . import Chunks, load_chunks, CreateChunksFile, OneChunk, ChunkFile
from .request import HTTPChunk, FirstChunk
from ...curl import PyCurlMulti, perform_multi
from ...error import PyCurlError, BadHeader
from ...util import fs_encode


class ChunksDownloading(object):

    def __init__(self, file_path, chunks):
        self.curl = PyCurlMulti()
        self.file_path = file_path
        self.info = chunks

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


class DownloadChunks(ChunksDownloading):

    def __init__(self, file_path, download, chunks):
        self._download = download

        super(DownloadChunks, self).__init__(file_path, chunks)

        self._chunks_number = chunks.count

        self.last_check = None
        self.log = download.log
        self._add_chunks()

    def checked_less_than(self, now, seconds=0.5):
        return not self.last_check or self.last_check + seconds < now

    def add_chunks_completed(self, completed):
        self.chunks_completed.update(completed)

    def _add_chunks(self):
        for chunk in self.info.chunks:
            http_chunk = HTTPChunk(chunk, self._download)

            self.chunks.append(http_chunk)
            self.curl.add_handle(http_chunk.curl)

    @property
    def size(self):
        return self._download.size

    def revert_to_one_connection(self):
        # list of chunks to clean and remove
        to_clean = [chunk for i, chunk in enumerate(self.chunks) if i > 0]

        for chunk in to_clean:
            self._remove(chunk)

        self.info = OneChunk(self._download.url, self.file_path, self.size)

    @property
    def initial(self):
        return self.chunks[0]

    def _remove(self, chunk):
        self._delete_chunk(chunk)

        self.chunks.remove(chunk)

    def _delete_chunk(self, chunk):
        self._close_chunk(chunk)

        chunk_name = fs_encode(self.info.get_chunk_path(chunk.id))
        remove(chunk_name)

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

    def __init__(self, file_path, download, chunk_number):
        chunks = self._create_chunks(file_path, download, chunk_number)
        super(DownloadMissingChunks, self).__init__(file_path, download, chunks)

    def _create_chunks(self, file_path, download, chunks_number):
        chunk = ChunkFile(1, 1, '%s.chunk%s' % (file_path, 0), (0, 1024))
        initial = FirstChunk(chunk, download)

        with PyCurlMulti() as curl:
            curl.add_handle(initial.curl)

            while not download.size:
                curl.perform()
                curl.select(1)

            curl.remove_handle(initial.curl)
            initial.close()

        return CreateChunksFile(download.url, file_path, download.size, chunks_number)


class ChunksDownload(DownloadChunks):

    def __new__(cls, file_path, download, chunks_number, resume):
        try:
            chunks = load_chunks(file_path, resume)

            download.size = chunks.size
            download.chunk_support = chunks.existing

            return DownloadChunks(file_path, download, chunks)
        except IOError:
            return DownloadMissingChunks(file_path, download, chunks_number)


def _check_chunks_done(download):
    now = time()

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

            if len(chunks_completed) == len(download.chunks):
                pass

            if len(chunks_completed) > len(download.chunks):
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