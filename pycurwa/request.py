#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pycurl

from httpy.http.headers import headers_raw_to_dict

from error import BadHeader, bad_headers
from .curl import Curl, BytesIO, curl_request, set_low_speed_timeout, set_auth, get_cookies, set_cookies, \
    get_status_code, set_network_options, set_headers, get_effective_url, set_body_fun, set_header_fun, \
    unset_cookie_files, set_request_context
from .response import decode_response


def _set_options(curl, options):
    interface, proxy, ipv6 = options.interface(), options.proxy(), options.ipv6_enabled()

    set_network_options(curl, interface, proxy, ipv6)

    auth, timeout = options.auth(), options.timeout()
    if auth in options:
        set_auth(curl, auth)

    if timeout in options:
        set_low_speed_timeout(curl, timeout)


class CurlRequestBase(object):
    def __init__(self, writer, cookies=None, bucket=None):
        self.curl = Curl()

        self.headers = {}
        self.cookies = cookies

        self._bucket = bucket
        self._header_str = ''

        curl_request(self.curl)

        self._header_parse = True

        if self._header_parse:
            set_header_fun(self.curl, self._write_header)
        set_body_fun(self.curl, self._write_body)

        if cookies:
            unset_cookie_files(self.curl)
            self._set_curl_cookies(self.curl)

        self.received = 0
        self._response_writer = writer

    def _add_curl_cookies(self):
        if self.cookies:
            self.cookies.add_cookies(get_cookies(self.curl))

    def _set_curl_cookies(self, curl):
        if self.cookies:
            for cookie in self.cookies.get_cookies():
                set_cookies(curl, cookie)

    def _write_header(self, buf):
        self._header_str += buf

        self._parse_header(buf)

    def _parse_header(self, buf):
        if self._header_str.endswith('\r\n\r\n'):
            self.headers = self._parse_http_header()

    def _parse_http_header(self):
        return headers_raw_to_dict(self._header_str)

    def _write_body(self, buf):
        size = len(buf)

        self.received += size

        self._response_writer(buf)

        if self._bucket:
            self._bucket.sleep_if_above_rate(received=size)

    def head(self, follow_redirect=True):
        if not follow_redirect:
            self.curl.setopt(pycurl.FOLLOWLOCATION, 0)

        self.curl.setopt(pycurl.NOBODY, 1)
        self.curl.perform()

        if not follow_redirect:
            self.curl.setopt(pycurl.FOLLOWLOCATION, 1)

        self.curl.setopt(pycurl.NOBODY, 0)
        return self.headers

    def verify_header(self):
        code = get_status_code(self.curl)

        if code in bad_headers:
            # 404 will NOT raise an exception
            raise BadHeader(code)
        return code


class CurlRequest(CurlRequestBase):
    def __init__(self, request, writer, cookies=None, bucket=None):
        super(CurlRequest, self).__init__(writer, cookies, bucket)
        self.request = request
        self.url = request.url
        set_request_context(self.curl, self.url)


class CurlRequests(CurlRequestBase):
    def __init__(self, cookies=None):
        self._rep = BytesIO()
        super(CurlRequests, self).__init__(self._rep.write, cookies)

    def load(self, url, get=None, post=None, referrer=True, cookies=True, multi_part=False, decode=False):
        set_request_context(self.curl, url, get, post, referrer, multi_part)

        set_headers(self.curl, self.headers)

        self.curl.perform()
        rep = self._get_response()

        self.curl.setopt(pycurl.POSTFIELDS, '')

        response_url = get_effective_url(self.curl)

        code = self.verify_header()

        self._add_curl_cookies()

        if decode:
            rep = decode_response(rep, self._header_str)

        return rep

    def _get_response(self):
        if self._rep is None:
            return ''

        value = self._rep.getvalue()
        self._rep.close()

        return value

    def close(self):
        self._rep.close()
        self.curl.close()