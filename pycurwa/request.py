#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pycurl

from httpy import HttpRequest
from httpy.error import error_status, HttpStatusError

from .curl import Curl, BytesIO
from .curl.request import curl_request
from .response import CurlResponse, CurlResponseBase


class CurlRequestBase(HttpRequest):

    def __init__(self, method, url, headers=None, data=None, cookies=None):
        super(CurlRequestBase, self).__init__(method, url, headers, data)

        self._curl = Curl()
        self.handle = self._curl.curl

        curl_request(self._curl, url, method, post_data=data, referrer=self.headers.get('referer'))

        self._cookies = cookies

        if cookies:
            self._curl.unset_cookie_files()
            self._set_curl_cookies()

        self.header_parse = True
        self._response = None

    def execute(self):
        self._curl.perform()

        error = self.get_status_error()
        if error:
            raise error

        return self._response

    def get_status_error(self):
        code = self._response.get_status_code()

        if code != 404 and code in error_status:
            return HttpStatusError(self, code)

    def _set_curl_cookies(self):
        for cookie in self._cookies.get_cookies():
            self._curl.set_cookies(cookie)

    def close(self):
        self.handle.close()


class CurlRequest(CurlRequestBase):

    def __init__(self, writer, method, url, headers=None, data=None, cookies=None, bucket=None):
        super(CurlRequest, self).__init__(method, url, headers, data, cookies)
        self._response = CurlResponse(self, writer, bucket)


class CurlHeadersRequest(CurlRequestBase):

    def __init__(self, url, headers=None, data=None, cookies=None):
        super(CurlHeadersRequest, self).__init__('HEAD', url, headers, data, cookies)
        self._response = CurlResponseBase(self)


class CurlRequests(CurlRequest):
    def __init__(self, cookies=None):
        self._rep = BytesIO()
        super(CurlRequests, self).__init__(self._rep.write, cookies)

    def load(self, url, get=None, post=None, referrer=True, cookies=True, multi_part=False, decode=False):
        self._curl.set_request_context(url, get, post, referrer, multi_part)

        self._curl.set_headers(self.headers)

        self._curl.perform()

        rep = self._get_response()

        self._curl.setopt(pycurl.POSTFIELDS, '')

        response_url = self._curl.get_effective_url()

        self._add_curl_cookies()

        return rep

    def _add_curl_cookies(self):
        if self._cookies:
            self._cookies.add_cookies(self._curl.get_cookies())

    def _get_response(self):
        if self._rep is None:
            return ''

        value = self._rep.getvalue()
        self._rep.close()

        return value

    def close(self):
        self._rep.close()
        self._curl.close()