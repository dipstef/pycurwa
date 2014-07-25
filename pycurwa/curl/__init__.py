from contextlib import closing
import pycurl
import sys
from urllib import urlencode
from unicoder import byte_string
from httpy.client.requests import user_agent
from urlo import params_url
from .error import PyCurlError


py3 = sys.version_info[0] == 3

if py3:
    from io import BytesIO
else:
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO


class ClosingCurl(closing):

    def __init__(self, curl_class):
        self.curl = curl_class()
        super(ClosingCurl, self).__init__(self)

    def __eq__(self, other):
        return other == self.curl

    def __getattr__(self, item):
        return getattr(self.curl, item)


class CurlMulti(ClosingCurl):

    def __init__(self):
        super(CurlMulti, self).__init__(pycurl.CurlMulti)

    def add_handle(self, curl):
        if isinstance(curl, Curl):
            curl = curl.curl
        self.curl.add_handle(curl)

    def remove_handle(self, curl):
        if isinstance(curl, Curl):
            curl = curl.curl
        self.curl.remove_handle(curl)

    def execute(self):
        while True:
            ret, num_handles = self.curl.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break


class Curl(ClosingCurl):

    def __init__(self):
        super(Curl, self).__init__(pycurl.Curl)

    def set_proxy(self, proxy):
        if proxy.type == "socks4":
            self.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS4)
        elif proxy.type == "socks5":
            self.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
        else:
            self.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
        self.setopt(pycurl.PROXY, proxy.address)
        self.setopt(pycurl.PROXYPORT, proxy.port)
        if proxy.auth:
            self.setopt(pycurl.PROXYUSERPWD, str("%s:%s" % (proxy.user, proxy.password)))

    def set_interface(self, interface):
        self.setopt(pycurl.INTERFACE, interface)

    def set_ipv6_resolve(self):
        self.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_WHATEVER)

    def set_ipv4_resolve(self):
        self.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V4)

    def set_auth(self, auth):
        self.setopt(pycurl.USERPWD, auth)

    def set_low_speed_timeout(self, timeout):
        self.setopt(pycurl.LOW_SPEED_TIME, timeout)

    def set_cookies(self, cookie):
        self.setopt(pycurl.COOKIELIST, cookie)

    def clear_cookies(self):
        self.unsetopt(self, pycurl.COOKIELIST)

    def unset_cookie_files(self):
        self.unsetopt(pycurl.COOKIEFILE)
        self.unsetopt(pycurl.COOKIEJAR)

    def set_url(self, url):
        self.setopt(pycurl.URL, url)

    def set_referrer(self, referrer):
        self.setopt(pycurl.REFERER, referrer)

    def set_headers(self, headers):
        self.setopt(pycurl.HTTPHEADER, headers)

    def set_network_options(self, interface=None, proxy=None, use_ipv6=False):
        if interface:
            self.set_interface(interface)
        if proxy:
            self.set_proxy(proxy)
        if use_ipv6:
            self.set_ipv6_resolve()
        else:
            self.set_ipv4_resolve()

    def set_range(self, bytes_range):
        self.setopt(pycurl.RANGE, bytes_range)

    def set_resume(self, resume):
        self.setopt(pycurl.RESUME_FROM, resume)

    def set_body_fun(self, body):
        self.setopt(pycurl.WRITEFUNCTION, body)

    def set_header_fun(self, header):
        self.setopt(pycurl.HEADERFUNCTION, header)

    def set_request_context(self, url, params=None, post_data=None, referrer=None, multi_part=False):
        url = byte_string(url)
        url = params_url(url, urlencode(params)) if params else url

        self.set_url(url)

        if post_data:
            post_request(self, post_data, multi_part)
        else:
            unset_post(self)

        if referrer:
            self.set_referrer(referrer)

    def get_effective_url(self):
        return self.getinfo(pycurl.EFFECTIVE_URL)

    def get_cookies(self):
        return self.getinfo(pycurl.INFO_COOKIELIST)

    def get_status_code(self):
        return int(self.getinfo(pycurl.RESPONSE_CODE))

    def get_speed_download(self):
        return self.getinfo(pycurl.SPEED_DOWNLOAD)


_default_headers = ["Accept: */*",
                    "Accept-Language: en-US,en",
                    "Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7",
                    "Connection: keep-alive",
                    "Keep-Alive: 300", "Expect:"]


def curl_request(curl, verbose=False):
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)
    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.NOSIGNAL, 1)
    curl.setopt(pycurl.NOPROGRESS, 1)

    if hasattr(pycurl, "AUTOREFERER"):
        curl.setopt(pycurl.AUTOREFERER, 1)

    curl.setopt(pycurl.SSL_VERIFYPEER, 0)
    curl.setopt(pycurl.LOW_SPEED_TIME, 30)
    curl.setopt(pycurl.LOW_SPEED_LIMIT, 5)

    if verbose:
        curl.setopt(pycurl.VERBOSE, 1)

    curl.setopt(pycurl.USERAGENT, user_agent)

    if pycurl.version_info()[7]:
        curl.setopt(pycurl.ENCODING, "gzip, deflate")

    curl.setopt(pycurl.HTTPHEADER, _default_headers)


def set_post(curl):
    curl.setopt(pycurl.POST, 1)


def unset_post(curl):
    curl.setopt(pycurl.POST, 0)


def post_request(curl, post, multi_part=False):
    set_post(curl)

    if not multi_part:
        if type(post) == unicode:
            post = str(post)  # unicode not allowed
        elif not type(post) == str:
            from ..util import url_encode
            post = url_encode(post)

        curl.setopt(pycurl.POSTFIELDS, post)
    else:
        post = [(x, byte_string(y)) for x, y in post.iteritems()]
        curl.setopt(pycurl.HTTPPOST, post)