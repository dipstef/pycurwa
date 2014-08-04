from httpy import HttpRequest
from httpy.error import error_status, HttpStatusError

from .curl import Curl
from .curl.request import curl_request
from .cookies import get_cookie_string
from .response import CurlResponseBase, CurlBodyResponse


class CurlRequestBase(HttpRequest):

    def __init__(self, request, cookies=None):
        super(CurlRequestBase, self).__init__(request.method, request.url, request.headers, request.data)

        self._curl = Curl()
        self.handle = self._curl.curl

        curl_request(self._curl, request, referrer=self.headers.get('referer'))

        self._cookies = cookies

        if cookies:
            self._curl.unset_cookie_files()
            self._set_curl_cookies()

        self.header_parse = True

    def get_status_error(self):
        code = self._curl.get_status_code()

        if code != 404 and code in error_status:
            return HttpStatusError(self, code)

    def _set_curl_cookies(self):
        cookie = get_cookie_string(self._cookies, self)
        if cookie:
            self._curl.set_cookie(cookie)

    def close(self):
        self.handle.close()


class CurlRequest(CurlRequestBase):

    def __init__(self, request, cookies=None, bucket=None):
        super(CurlRequest, self).__init__(request, cookies=cookies)
        self._bucket = bucket

    def execute(self):
        response = CurlBodyResponse(self, self._cookies, self._bucket)

        self._curl.perform()

        error = self.get_status_error()
        if error:
            raise error

        return response


class CurlHeadersRequest(CurlRequestBase):

    def __init__(self, url, headers=None, data=None, cookies=None):
        super(CurlHeadersRequest, self).__init__(HttpRequest('HEAD', url, headers, data), cookies)

        self._response = CurlResponseBase(self, self._cookies)