from abc import abstractmethod

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
        self.handle = self._curl.handle

        curl_request(self._curl, request)

        self._cookies = cookies

        if cookies:
            self._set_curl_cookies()

        self._response = self._create_response()

    def _set_curl_cookies(self):
        cookie = self._cookies.get_cookie_string(self)
        if cookie:
            self._curl.set_cookie(cookie)

    @abstractmethod
    def _create_response(self):
        raise CurlResponseBase(self, self._cookies)

    def get_response(self):
        return self._response

    def close(self):
        self._response.close()


class CurlRequest(CurlRequestBase):

    def __init__(self, request, cookies=None, bucket=None):
        self._bucket = bucket
        super(CurlRequest, self).__init__(request, cookies=cookies)

    def execute(self):
        try:
            return self._execute()
        except PyCurlError, e:
            raise HttpCurlError(self, e.curl_errno, e.curl_message)
        finally:
            self.close()

    def _execute(self):
        self._curl.perform()

        code = self._curl.get_status_code()

        if code in error_status:
            raise HttpStatusError(self, code)

        return self._response

    def _create_response(self):
        return CurlBodyResponse(self, self._cookies, self._bucket)