import os
import time

from httpy import HttpHeaders, HttpRequest
from httpy.http.headers.content import disposition_file_name, content_length

from ..curl import set_resume, get_speed_download
from ..request import CurlRequest
from ..util import fs_encode


class HttpDownloadRequest(CurlRequest):

    def __init__(self, url, file_path, cookies, bucket=None, resume=False):
        self._sleep = 0.000
        self._last_size = 0
        self._resume = resume

        self.path = fs_encode(file_path)

        self._fp = open(file_path, 'ab' if resume else 'wb')

        super(HttpDownloadRequest, self).__init__(HttpRequest('GET', url), self._fp.write, cookies, bucket)

        if resume:
            self._handle_resume()
            self.received = self._fp.tell() or os.stat(self.path).st_size
        else:
            self._handle_not_resumed()

    def _handle_resume(self):
        set_resume(self.curl, self.received)

    def _handle_not_resumed(self):
        pass

    def _write_body(self, buf):
        super(HttpDownloadRequest, self)._write_body(buf)
        if not self._bucket:
            self._update_sleep(len(buf))

            time.sleep(self._sleep)

    def _update_sleep(self, size):
        # Avoid small buffers, increasing sleep time slowly if buffer size gets smaller
        # otherwise reduce sleep time by percentage (values are based on tests)
        # So in general cpu time is saved without reducing bandwidth too much
        self._last_size = size
        if size < self._last_size:
            self._sleep += 0.002
        else:
            self._sleep *= 0.7

    def _parse_header(self, buf):
        super(HttpDownloadRequest, self)._parse_header(buf)
        self.headers = DownloadHeaders(self.headers)

    def get_speed(self):
        return get_speed_download(self.curl)

    def close(self):
        self._flush()
        self.curl.close()

    def _flush(self):
        self._fp.flush()
        os.fsync(self._fp.fileno())
        self._fp.close()

    @property
    def disposition_name(self):
        return self.headers.file_name

    @property
    def size(self):
        return self.headers.size


class DownloadHeaders(HttpHeaders):

    @property
    def chunk_support(self):
        return 'bytes' == self.get('accept-ranges', '')

    @property
    def file_name(self):
        return disposition_file_name(self)

    @property
    def size(self):
        return content_length(self)