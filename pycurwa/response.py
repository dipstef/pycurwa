from datetime import datetime
from httpy import ResponseStatus, HttpHeaders, date_header
from httpy.http.headers import header_string_to_dict
from .curl import BytesIO


class CurlResponseBase(ResponseStatus):

    __headers__ = True

    def __init__(self, request, cookies=None):
        self._curl = request._curl
        self.handle = request.handle

        self.request = request

        self._header_str = ''
        #keeps tracks of the headers received from redirects
        self._requests_headers = []

        if self.__headers__:
            self._curl.set_header_fun(self._write_header)

        self._date = datetime.utcnow()
        self._cookies = cookies

        self._headers = None
        self._parsed = None

        self._response_url = None
        self._status_code = None
        self._closed = False

    def _write_header(self, buf):
        self._header_str += buf

        if self._header_str.endswith('\r\n\r\n'):
            self._parse_header(self._header_str)
            #reset header in case of redirect reset headers
            self._header_str = ''
            self._requests_headers.append(self._headers)

    def _parse_header(self, header_string):
        headers = header_string_to_dict(header_string)
        self._headers = HttpHeaders(headers)
        self._parsed = datetime.utcnow()

    def _set_cookies(self):
        if self._cookies is not None:
            self._cookies.add_cookies(self._curl.get_cookies())

    def _set_status_code(self):
        if not self._status_code:
            self._status_code = self._curl.get_status_code()

    def _set_response_url(self):
        if not self._response_url:
            self._response_url = self._curl.get_response_url()

    def close(self):
        if not self._closed:
            self._close()
            self._closed = True

    def _close(self):
        self._set_cookies()
        self._set_response_url()
        self._set_status_code()
        self._curl.close()

    @property
    def url(self):
        return self._response_url

    @property
    def status(self):
        return self._status_code

    @property
    def headers(self):
        return self._headers

    @property
    def date(self):
        return date_header(self.headers) if self.headers else self._parsed


class CurlResponse(CurlResponseBase):

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
        return self._read()

    def _read(self):
        self._body = self._bytes.getvalue()
        self._bytes.close()
        return self._body

    @property
    def body(self):
        if self._body is None:
            self._body = self.read()
        return self._body