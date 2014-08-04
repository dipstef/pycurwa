from httpy import ResponseStatus, HttpHeaders
from httpy.http.headers import headers_raw_to_dict
from .curl import BytesIO


class CurlResponseBase(object):
    __headers_class__ = HttpHeaders

    def __init__(self, request):
        self._curl = request._curl
        self.handle = request.handle

        self.request = request

        self._header_str = ''

        self.headers = self.__headers_class__()

        if request.header_parse:
            self._curl.set_header_fun(self._write_header)

    def _write_header(self, buf):
        self._header_str += buf

        self._parse_header()

    def _parse_header(self):
        if self._header_str.endswith('\r\n\r\n'):
            self.headers.clear()
            self.headers.update(self._parse_http_header())

    def _parse_http_header(self):
        return headers_raw_to_dict(self._header_str)

    def get_status_code(self):
        code = self._curl.get_status_code()
        return code


class CurlResponseStatus(CurlResponseBase, ResponseStatus):

    def __init__(self, request):
        super(CurlResponseStatus, self).__init__(request)

    @property
    def url(self):
        return self._curl.get_effective_url()

    @property
    def status(self):
        return self.get_status_code()


class CurlResponse(CurlResponseStatus):

    def __init__(self, request, writer, bucket=None):
        super(CurlResponse, self).__init__(request)
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

    def __init__(self, request, bucket=None):
        self._bytes = BytesIO()
        super(CurlBodyResponse, self).__init__(request, self._bytes.write, bucket)
        self._curl.headers_only()
        self._body = None

    def read(self, *args, **kwargs):
        self._curl.enable_body_retrieve()

        self._curl.perform()
        body = self._bytes.getvalue()
        self.close()
        return body

    @property
    def body(self):
        if self._body is None:
            self._body = self.read()
        return self._body

    def close(self):
        self._bytes.close()
        self.handle.close()
