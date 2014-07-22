import codecs
import os
import re
import time

import pycurl
from unicoder import to_unicode

from .error import WrongFormat, BadHeader, RangeNotSatisfiable
from .request import HTTPRequestBase
from .util import fs_encode


class ChunkInfo(object):
    def __init__(self, name, size=0, resume=False, existing=False):
        #add url
        self.name = to_unicode(name)
        self.size = size
        self.resume = resume
        self.existing = existing
        self.chunks = []

    def __repr__(self):
        ret = 'ChunkInfo: %s, %s\n' % (self.name, self.size)
        for i, c in enumerate(self.chunks):
            ret += '%s# %s\n' % (i, c[1])

        return ret

    def set_size(self, size):
        self.size = int(size)

    def add_chunk(self, name, range):
        self.chunks.append((name, range))

    def clear(self):
        self.chunks = []

    def create_chunks(self, chunks):
        self.clear()
        chunk_size = self.size / chunks

        current = 0
        for i in range(chunks):
            end = self.size - 1 if (i == chunks - 1) else current + chunk_size

            self.add_chunk('%s.chunk%s' % (self.name, i), (current, end))

            current += chunk_size + 1

    def save(self):
        fs_name = fs_encode('%s.chunks' % self.name)

        with codecs.open(fs_name, 'w', 'utf_8') as chunks_file:
            chunks_file.write('name:%s\n' % self.name)
            chunks_file.write('size:%s\n' % self.size)

            for i, c in enumerate(self.chunks):
                chunks_file.write('#%d:\n' % i)
                chunks_file.write('\tname:%s\n' % c[0])
                chunks_file.write('\trange:%i-%i\n' % c[1])


    @staticmethod
    def load(name, resume=False):
        fs_name = fs_encode('%s.chunks' % name)

        with codecs.open(fs_name, 'r', 'utf_8') as fh:

            name = fh.readline()[:-1]
            size = fh.readline()[:-1]

            if name.startswith('name:') and size.startswith('size:'):
                name = name[5:]
                size = int(size[5:])
            else:
                raise WrongFormat()

            chunk_info = ChunkInfo(name, size=size, resume=resume, existing=True)

            while True:
                if not fh.readline():
                    break
                name = fh.readline()[1:-1]
                bytes_range = fh.readline()[1:-1]

                if name.startswith('name:') and bytes_range.startswith('range:'):
                    name = name[5:]
                    bytes_range = bytes_range[6:].split('-')
                else:
                    raise WrongFormat()

                chunk_info.add_chunk(name, (long(bytes_range[0]), long(bytes_range[1])))

            return chunk_info

    def remove(self):
        fs_name = fs_encode('%s.chunks' % self.name)
        if os.path.exists(fs_name):
            os.remove(fs_name)

    def get_count(self):
        return len(self.chunks)

    def get_chunk_name(self, index):
        return self.chunks[index][0]

    def get_chunk_range(self, index):
        return self.chunks[index][1]


class DownloadHeader(object):

    def __init__(self, file_name=None, size=0, chunks_allowed=False):
        self.file_name = file_name
        self.size = size
        self.chunk_support = chunks_allowed

    def parse(self, header_string, resume=False):
        for line in header_string:
            line = line.strip().lower()
            if line.startswith('accept-ranges') and 'bytes' in line:
                self.chunk_support = True

            if line.startswith('content-disposition') and 'filename=' in line:
                name = line.partition('filename=')[2]
                name = name.replace(''', '').replace(''', '').replace(';', '').strip()

                self.file_name = name

            if not resume and line.startswith('content-length'):
                self.size = int(line.split(':')[1])


class HttpDownloadRequest(HTTPRequestBase):

    def __init__(self, url, file_path, cookies, log, bucket=None, resume=False, get=None, post=None, referrer=None):
        super(HttpDownloadRequest, self).__init__(cookies)
        self.url = url

        self.arrived = 0

        self._header_parsed = None

        self._fp = None

        # check and remove byte order mark
        self._bom_checked = False

        self.sleep = 0.000
        self._last_size = 0
        self._resume = resume

        self.log = log
        self._bucket = bucket

        self.file_path = fs_encode(file_path)

        self._set_request_context(url, get, post, referrer, cookies)

        self.curl.setopt(pycurl.WRITEFUNCTION, self._write_body)
        self.curl.setopt(pycurl.HEADERFUNCTION, self._write_header)

        # request all bytes, since some servers in russia seems to have a defect arithmetic unit

        if self._resume:
            self._fp = open(file_path, 'ab')

            self.arrived = self._fp.tell()

            if not self.arrived:
                self.arrived = os.stat(self.file_path).st_size

            self._handle_resume()
        else:
            self._handle_not_resumed()

    def _handle_resume(self):
        self.log.debug('Resume File from %i' % self.arrived)
        self.curl.setopt(pycurl.RESUME_FROM, self.arrived)

    def _handle_not_resumed(self):
        self._fp = open(self.file_path, 'wb')

    def _write_body(self, buf):
        buf = self._check_bom(buf)

        size = len(buf)

        self.arrived += size

        self._fp.write(buf)

        if self._bucket:
            self._bucket.sleep_above_rate(size)
        else:
            self._update_sleep(size)

            self._last_size = size

            time.sleep(self.sleep)

    def _check_bom(self, buf):
        # ignore BOM, it confuses unrar
        if not self._bom_checked:
            if [ord(b) for b in buf[:3]] == [239, 187, 191]:
                buf = buf[3:]
            self._bom_checked = True
        return buf

    def _update_sleep(self, size):
        # Avoid small buffers, increasing sleep time slowly if buffer size gets smaller
        # otherwise reduce sleep time by percentage (values are based on tests)
        # So in general cpu time is saved without reducing bandwidth too much
        if size < self._last_size:
            self.sleep += 0.002
        else:
            self.sleep *= 0.7

    def _write_header(self, buf):
        self.header += buf

        self._parse_header(buf)

    def _parse_header(self, buf):
        # @TODO forward headers?, this is possibly un-needed, when we just parse valid 200 headers

        if self.header.endswith('\r\n\r\n'):
            self._header_parsed = self._parse_http_header()
        #ftp file size parsing
        elif buf.startswith('150') and 'data connection' in buf:
            self._header_parsed = self._parse_ftp_header(buf)

    def _parse_http_header(self):
        header = DownloadHeader()

        header_string = self.decode_response(self.header).splitlines()
        header.parse(header_string, resume=self._resume)

        return header

    def _parse_ftp_header(self, buf):
        header = DownloadHeader()

        size = re.search(r'(\d+) bytes', buf)

        if size:
            header.size = int(size.group(1))
            header.chunk_support = True

        return header

    def flush_file(self):
        self._fp.flush()
        os.fsync(self._fp.fileno()) #make sure everything was written to disk
        self._fp.close() #needs to be closed, or merging chunks will fail

    def close(self):
        self._fp.close()
        self.curl.close()


class HttpDownloadRange(HttpDownloadRequest):

    def __init__(self, url, file_path, cookies, log, bytes_range, full_size=None, bucket=None, resume=False):
        self._range = bytes_range
        self._full_size = full_size
        super(HttpDownloadRange, self).__init__(url, file_path, cookies, log, bucket, resume)

    def _handle_resume(self):
        if self._range:
            self._set_resume_range()
        else:
            super(HttpDownloadRange, self)._handle_resume()

    def _set_resume_range(self):
        # do nothing if chunk already finished
        if self.arrived + self._range[0] >= self._range[1]:
            return None

        self._set_bytes_range(self.arrived)

    def _handle_not_resumed(self):
        super(HttpDownloadRange, self)._handle_not_resumed()
        if self._range:
            self._set_bytes_range()

    def _set_bytes_range(self, arrived=0):
        # as last chunk don't set end bytes_range, so we get everything
        if not self._full_size:
            bytes_range = '%i-' % (arrived + self._range_from)
        else:
            bytes_range = '%i-%i' % (arrived + self._range_from, min(self._range_to + 1, self._full_size - 1))

        self.curl.setopt(pycurl.RANGE, bytes_range)
        return bytes_range

    def _write_body(self, buf):
        super(HttpDownloadRange, self)._write_body(buf)
        if self._range and self.arrived > self._range_size:
            return 0

    def _parse_header(self, buf):
        # as first chunk, we will parse the headers
        if not self._range:
            super(HttpDownloadRange, self)._parse_header(buf)

    def stop(self):
        '''The download will not proceed after next call of _write_body'''
        self._range = [0, 0]

    def reset_range(self):
        ''' Reset the range, so the download will load all data available  '''
        self._range = None

    def set_range(self, bytes_range):
        self._range = bytes_range

    @property
    def _range_from(self):
        return self._range[0]

    @property
    def _range_to(self):
        return self._range[1]

    @property
    def _range_size(self):
        return self._range_to - self._range_from if self._range else 0

    def verify_header(self):
        try:
            return super(HttpDownloadRange, self).verify_header()
        except BadHeader, e:
            if e.code == 416:
                raise RangeNotSatisfiable(self.url, self.file_path, self._range)
            raise e


class HTTPChunk(HttpDownloadRange):

    def __init__(self, chunk_id, download, info, bytes_range):
        download_size = download.size if chunk_id < len(info.chunks) - 1 else None

        file_path = info.get_chunk_name(chunk_id)
        self.id = chunk_id

        super(HTTPChunk, self).__init__(download.url, file_path, download.cookies, download.log, bytes_range,
                                        download_size, download.bucket, info.resume)
        self._info = info

        self._download = download

    def __repr__(self):
        return '<HTTPChunk id=%d, size=%d, arrived=%d>' % (self.id, self._range_size, self.arrived)


class FirstChunk(HTTPChunk):
    def __init__(self, download, info):
        super(FirstChunk, self).__init__(0, download, info, None)

    def _parse_http_header(self):
        header = super(FirstChunk, self)._parse_http_header()
        self._set_header(header)
        return header

    def _parse_ftp_header(self, buf):
        header = super(FirstChunk, self)._parse_ftp_header(buf)
        self._set_header(header)
        return header

    def _set_header(self, header):
        self._download.disposition_name = header.file_name
        self._download.size = header.size
        self._download.chunk_support = header.chunk_support