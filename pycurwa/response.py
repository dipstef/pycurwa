from datetime import datetime
from httpy import ResponseStatus, HttpHeaders, date_header
from httpy.http.headers import header_string_to_dict
from .curl import BytesIO
from .cookies import write_cookies


class CurlResponseBase(object):
    __headers__ = HttpHeaders

    def __init__(self, request, cookies=None):
        self._curl = request._curl
        self.handle = request.handle

        self.request = request

        self._header_str = ''

        if self.__headers__:
            self._curl.set_header_fun(self._write_header)

        self._date = datetime.utcnow()
        self._cookies = cookies

        self._status_code = None

    def _write_header(self, buf):
        self._header_str += buf

        if self._header_str.endswith('\r\n\r\n'):
            self._parse_http_header()

    def _parse_http_header(self):
        headers = self.__headers__(header_string_to_dict(self._header_str))

        self.headers = headers

        self._date = date_header(headers) or datetime.utcnow()

        if self._cookies is not None:
            write_cookies(self._cookies, headers, self.request)

        return headers

    def get_status_code(self):
        self._set_status_code()
        return self._status_code

    def _set_status_code(self):
        if not self._status_code:
            self._status_code = self._curl.get_status_code()

    def close(self):
        self._set_status_code()
        self._curl.close()


class CurlResponseStatus(CurlResponseBase, ResponseStatus):

    def __init__(self, request, cookies=None):
        super(CurlResponseStatus, self).__init__(request, cookies)

    @property
    def url(self):
        return self._curl.get_response_url()

    @property
    def status(self):
        return self.get_status_code()

    @property
    def date(self):
        return self._date


class CurlResponse(CurlResponseStatus):

    def __init__(self, request, writer, cookies, bucket=None):
        super(CurlResponse, self).__init__(request, cookies)
        self._bucket = bucket

        self.received = 0

        self._response_writer = writer
        self._curl.set_body_fun(self._write_body)

    def _write_body(self, buf):
        size = len(buf)

        self.received += size

        self._response_writer(buf)

        if self._bucket:
            self._bucket.sleep_if_above_rate(received=size)


class CurlBodyResponse(CurlResponse):

    def __init__(self, request, cookies, bucket=None):
        self._bytes = BytesIO()
        super(CurlBodyResponse, self).__init__(request, self._bytes.write, cookies, bucket)
        self._body = None

    def read(self):
        try:
            return self._read()
        finally:
            self.close()

    def _read(self):
        self._body = self._bytes.getvalue()
        self._bytes.close()
        return self._body

    @property
    def body(self):
        if self._body is None:
            self._body = self.read()
        return self._body