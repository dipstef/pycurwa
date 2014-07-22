#!/usr/bin/env python
# -*- coding: utf-8 -*-
from codecs import getincrementaldecoder, lookup, BOM_UTF8
from logging import getLogger
from cStringIO import StringIO
from urllib import urlencode

from unicoder import byte_string
from urlo import quote
import pycurl

from error import Abort, BadHeader, bad_headers
from options import Options
from curl import post_request, set_proxy, curl_request, set_interface, set_ipv6_resolve, set_ipv4_resolve, \
    set_low_speed_timeout, set_auth, get_cookies, set_cookies, clear_cookies, set_url, set_referrer


def _set_options(curl, options):
    interface, proxy, ipv6 = options.interface(), options.proxy(), options.ipv6_enabled()

    if interface:
        set_interface(curl, str(interface))

    if proxy:
        set_proxy(curl, proxy)

    if ipv6:
        set_ipv6_resolve(curl)
    else:
        set_ipv4_resolve(curl)

    auth, timeout = options.auth(), options.timeout()

    if auth in options:
        set_auth(curl, auth)

    if timeout in options:
        set_low_speed_timeout(curl, timeout)


class HTTPRequestBase(object):
    def __init__(self, cookies=None, options=None):
        self.curl = pycurl.Curl()

        self.cookies = cookies  # cookiejar

        self.header = ''

        self._init_handle()
        if options:
            _set_options(self.curl, Options(options))

    def _init_handle(self):
        ''' sets common options to curl handle '''
        curl_request(self.curl)

    def _add_curl_cookies(self, curl):
        ''' put cookies from curl handle to cj '''
        if self.cookies:
            self.cookies.add_cookies(get_cookies(curl))

    def _set_curl_cookies(self, curl):
        ''' add cookies from cj to curl handle '''
        if self.cookies:
            for cookie in self.cookies.get_cookies():
                set_cookies(curl, cookie)
        return

    def clear_cookies(self):
        clear_cookies(self.curl)

    def _set_request_context(self, url, params, post_data, referrer, cookies, multi_part=False):
        ''' sets everything needed for the request '''
        url = quote(byte_string(url))

        if params:
            params = urlencode(params)
            url = '%s?%s' % (url, params)

        curl = self.curl

        set_url(curl, url)

        if post_data:
            post_request(curl, post_data, multi_part)
        else:
            curl.setopt(pycurl.POST, 0)

        if referrer:
            set_referrer(curl, str(referrer))

        if cookies:
            curl.setopt(pycurl.COOKIEFILE, '')
            curl.setopt(pycurl.COOKIEJAR, '')
            self._set_curl_cookies(curl)

    def decode_response(self, rep):
        ''' decode with correct encoding, relies on header '''
        header = self.header.splitlines()
        encoding = 'utf8'  # default encoding

        for line in header:
            line = line.lower().replace(' ', '')
            if not line.startswith('content-type:') or \
                    ('text' not in line and 'application' not in line):
                continue

            none, delimiter, charset = line.rpartition('charset=')
            if delimiter:
                charset = charset.split(';')
                if charset:
                    encoding = charset[0]

        # self.log.debug('Decoded %s' % encoding )
        if lookup(encoding).name == 'utf-8' and rep.startswith(BOM_UTF8):
            encoding = 'utf-8-sig'

        decoder = getincrementaldecoder(encoding)('replace')
        rep = decoder.decode(rep, True)

        # TODO: html_un-escape as default

        return rep

    def _write_header(self, buf):
        ''' writes header '''
        self.header += buf

    def verify_header(self):
        ''' raise an exceptions on bad headers '''
        code = int(self.curl.getinfo(pycurl.RESPONSE_CODE))

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
        self.lastEffectiveURL = None

        self.curl.setopt(pycurl.WRITEFUNCTION, self.write)
        self.curl.setopt(pycurl.HEADERFUNCTION, self._write_header)
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
        curl.setopt(pycurl.HTTPHEADER, self.headers)

        if just_header:
            rep = self._head_request(curl)
        else:
            curl.perform()
            rep = self.get_response()

        curl.setopt(pycurl.POSTFIELDS, '')

        self.lastEffectiveURL = curl.getinfo(pycurl.EFFECTIVE_URL)
        self.code = self.verify_header()

        self._add_curl_cookies(curl)

        if decode:
            rep = self.decode_response(rep)

        return rep

    def write(self, buf):
        ''' writes response '''
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
        ''' cleanup, unusable after this '''
        self._rep.close()
        self.curl.close()


def main():
    url = 'http://pyload.org'

    c = HTTPRequest()
    print c.load(url)


if __name__ == '__main__':
    main()