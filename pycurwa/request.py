from httpy.client import HttpyRequest
from httpy.error import error_status, HttpStatusError

from .curl import Curl, PyCurlError
from .curl.request import curl_request
from .curl.error import HttpCurlError
from .response import CurlResponseBase, CurlBodyResponse


class CurlRequestBase(HttpyRequest):

    def __init__(self, request, cookies=None):
        super(CurlRequestBase, self).__init__(request.method, request.url, request.headers, request.data,
                                              request.params, request.timeout, request.redirect)
        self._curl = Curl()
        self.handle = self._curl.curl

        curl_request(self._curl, request)

        self._cookies = cookies

        if cookies:
            self._set_curl_cookies()

    def get_status_error(self):
        code = self._curl.get_status_code()

        if code != 404 and code in error_status:
            return HttpStatusError(self, code)

    def _set_curl_cookies(self):
        cookie = self._cookies.get_cookie_string(self)
        if cookie:
            self._curl.set_cookie(cookie)

    def close(self):
        self.handle.close()


class CurlRequest(CurlRequestBase):

    def __init__(self, request, cookies=None, bucket=None):
        self._bucket = bucket
        super(CurlRequest, self).__init__(request, cookies=cookies)
        self._response = self._create_response()

    def execute(self):
        try:
            return self._execute()
        except PyCurlError, e:
            raise HttpCurlError(self, e.curl_errno, e.curl_message)
        finally:
            self.close()

    def _execute(self):
        self._curl.perform()

        error = self.get_status_error()
        if error:
            raise error
        return self._response

    def _create_response(self):
        return CurlBodyResponse(self, self._cookies, self._bucket)

    def get_response(self):
        return self._response

    def close(self):
        self._response.close()


class CurlHeadersRequest(CurlRequest):

    def __init__(self, url, headers=None, data=None, params=None, cookies=None):
        super(CurlHeadersRequest, self).__init__(HttpyRequest('HEAD', url, headers, data, params), cookies)

    def head(self):
        return self.execute().headers

    def _create_response(self):
        return CurlResponseBase(self, self._cookies)