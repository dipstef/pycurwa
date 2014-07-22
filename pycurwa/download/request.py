import os
import re
import time

import pycurl

from pycurwa.request import HTTPRequestBase
from pycurwa.util import fs_encode


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