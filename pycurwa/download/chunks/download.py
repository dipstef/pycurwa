from os import remove
from time import time
from procol.console import print_err
from pycurwa.error import BadHeader, PyCurlError
from .request import HTTPChunk, FirstChunk
from . import Chunks
from ...curl import PyCurlMulti, perform_multi
from ...error import PyCurlError
from ...util import fs_encode


class DownloadChunks(object):

    def __init__(self, file_path, chunks):
        self.curl = PyCurlMulti()
        self.file_path = file_path
        self.info = chunks

        self.chunks = []
        self.chunks_completed = set()

    def download_checks(self):
        while not self.is_done():
            perform_multi(self.curl)

            time_checked = _check_chunks_done(self)

            if not self.is_done():
                yield time_checked

                self.curl.select(1)

    def is_done(self):
        return len(self.chunks_completed) >= len(self.chunks)


class ChunksDownload(DownloadChunks):

    def __init__(self, file_path, download, chunks_number=1, resume=False):

        self._download = download

        chunks_info = _load_chunks_info(self.file_path, resume)
        download.size = self.info.size
        download.chunk_support = chunks_info.existing

        super(ChunksDownload, self).__init__(file_path, chunks_info)

        self._chunks_number = chunks_number if not chunks_info.existing else chunks_info.get_count()

        self.initial = self._create_initial_chunk()

        self._chunks_created = False
        self.last_check = None
        self.log = download.log

    def checked_less_than(self, now, seconds=0.5):
        return not self.last_check or self.last_check + seconds < now

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
        except PyCurlError, e:
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