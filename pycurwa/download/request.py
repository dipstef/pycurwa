import os
import re
import time

from ..curl import set_resume, set_body_header_fun, get_speed_download

from ..request import HTTPRequestBase
from ..util import fs_encode


class HttpDownloadRequest(HTTPRequestBase):

    def __init__(self, url, file_path, cookies, bucket=None, resume=False, get=None, post=None, referrer=None):
        super(HttpDownloadRequest, self).__init__(cookies)
        self.url = url

        self._header_parsed = None

        self._fp = None

        # check and remove byte order mark
        self._bom_checked = False

        self._sleep = 0.000
        self._last_size = 0
        self._resume = resume

        self._bucket = bucket

        self.path = fs_encode(file_path)

        self._set_request_context(url, get, post, referrer, cookies)

        self._header_parse = True

        set_body_header_fun(self.curl, body=self._write_body, header=self._header_parse and self._write_header)

        if self._resume:
            self._fp = open(file_path, 'ab')

            self.received = self._fp.tell() or os.stat(self.path).st_size

            self._handle_resume()
        else:
            self.received = 0
            self._handle_not_resumed()

    def _handle_resume(self):
        set_resume(self.curl, self.received)

    def _handle_not_resumed(self):
        self._fp = open(self.path, 'wb')

    def _write_body(self, buf):
        buf = self._check_bom(buf)

        size = len(buf)

        self.received += size

        self._fp.write(buf)

        if self._bucket:
            self._bucket.sleep_if_above_rate(received=size)
        else:
            self._update_sleep(size)

            self._last_size = size

            time.sleep(self._sleep)

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
            self._sleep += 0.002
        else:
            self._sleep *= 0.7

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

    def get_speed(self):
        return get_speed_download(self.curl)

    def flush_file(self):
        self._fp.flush()
        os.fsync(self._fp.fileno())
        self._fp.close()

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