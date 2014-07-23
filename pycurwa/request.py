#!/usr/bin/env python
# -*- coding: utf-8 -*-
from logging import getLogger
from cStringIO import StringIO
from time import time
from urllib import urlencode

from unicoder import byte_string
from urlo import params_url
import pycurl

from error import Abort, BadHeader, bad_headers
from options import Options
from .curl import post_request, curl_request, set_low_speed_timeout, set_auth, get_cookies, set_cookies, clear_cookies, \
    set_url, set_referrer, get_status_code, set_network_options, Curl, unset_post, unset_cookie_files, \
    set_body_header_fun, set_headers, get_effective_url
from .response import decode_response


def _set_options(curl, options):
    interface, proxy, ipv6 = options.interface(), options.proxy(), options.ipv6_enabled()

    set_network_options(curl, interface, proxy, ipv6)

    auth, timeout = options.auth(), options.timeout()
    if auth in options:
        set_auth(curl, auth)

    if timeout in options:
        set_low_speed_timeout(curl, timeout)


class HTTPRequestBase(object):
    def __init__(self, cookies=None, options=None):
        self.curl = Curl()

        self.cookies = cookies

        self.header = ''

        self._init_handle()
        if options:
            _set_options(self.curl, Options(options))

    def _init_handle(self):
        curl_request(self.curl)

    def _add_curl_cookies(self, curl):
        if self.cookies:
            self.cookies.add_cookies(get_cookies(curl))

    def _set_curl_cookies(self, curl):
        if self.cookies:
            for cookie in self.cookies.get_cookies():
                set_cookies(curl, cookie)

    def clear_cookies(self):
        clear_cookies(self.curl)

    def _set_request_context(self, url, params, post_data, referrer, cookies, multi_part=False):
        url = byte_string(url)
        url = params_url(url, urlencode(params)) if params else url

        set_url(self.curl, url)

        if post_data:
            post_request(self.curl, post_data, multi_part)
        else:
            unset_post(self.curl)

        if referrer:
            set_referrer(self.curl, str(referrer))

        if cookies:
            unset_cookie_files(self.curl)
            self._set_curl_cookies(self.curl)

    def decode_response(self, rep):
        ''' decode with correct encoding, relies on header '''
        return decode_response(rep, self.header)

    def _write_header(self, buf):
        self.header += buf

    def verify_header(self):
        code = get_status_code(self.curl)

        if code in bad_headers:
            # 404 will NOT raise an exception
            raise BadHeader(code)
        return code


class HTTPRequest(HTTPRequestBase):
    def __init__(self, cookies=None, options=None):
        super(HTTPRequest, self).__init__(cookies, options)

        self.abort = False
        self.code = 0  # last http code
        self.headers = []  # temporary request header

        self.lastURL = None
        self.response_url = None

        set_body_header_fun(self.curl, body=self._write_body, header=self._write_header)
        self._rep = StringIO()

        self.log = getLogger('log')

    def _head_request(self, curl):
        curl.setopt(pycurl.FOLLOWLOCATION, 0)
        curl.setopt(pycurl.NOBODY, 1)
        curl.perform()

        rep = self.header

        curl.setopt(pycurl.FOLLOWLOCATION, 1)
        curl.setopt(pycurl.NOBODY, 0)

        return rep

    def load(self, url, get={}, post={}, referer=True, cookies=True, just_header=False, multipart=False, decode=False):
        self._set_request_context(url, get, post, referer, cookies, multipart)

        self.header = ''

        curl = self.curl
        set_headers(self.curl, self.headers)

        if just_header:
            rep = self._head_request(curl)
        else:
            curl.perform()
            rep = self.get_response()

        curl.setopt(pycurl.POSTFIELDS, '')

        self.response_url = get_effective_url(self.curl)

        self.code = self.verify_header()

        self._add_curl_cookies(curl)

        if decode:
            rep = self.decode_response(rep)

        return rep

    def _write_body(self, buf):
        if self.abort:
            raise Abort()

        if self._rep.tell() > 1000000:
            rep = self.get_response()

            with open('response.dump', 'wb') as f:
                f.write(rep)
                raise Exception('Loaded Url exceeded limit')

        self._rep.write(buf)

    def get_response(self):
        ''' retrieve response from string io'''
        if self._rep is None:
            return ''
        value = self._rep.getvalue()

        self._rep.close()

        return value

    def put_header(self, name, value):
        self.headers.append('%s: %s' % (name, value))

    def clear_headers(self):
        self.headers = []

    def close(self):
        self._rep.close()
        self.curl.close()


class CookieJar(object):
    def __init__(self, domain):
        self._cookies = {}
        self.domain = domain

    def add_cookies(self, cookies_list):
        for c in cookies_list:
            name = c.split("\t")[5]
            self._cookies[name] = c

    def get_cookies(self):
        return self._cookies.values()

    def parse_cookie(self, name):
        if name in self._cookies:
            return self._cookies[name].split("\t")[6]
        else:
            return None

    def get_cookie(self, name):
        return self.parse_cookie(name)

    def set_cookie(self, domain, name, value, path="/", exp=time()+3600*24*180):
        s = ".%s	TRUE	%s	FALSE	%s	%s	%s" % (domain, path, exp, name, value)
        self._cookies[name] = s

    def clear(self):
        self._cookies = {}