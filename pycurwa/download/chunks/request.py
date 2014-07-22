import pycurl
from ..request import HttpDownloadRequest
from ...error import BadHeader, RangeNotSatisfiable


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