from contextlib import closing
import pycurl
from unicoder import byte_string
from httpy.client.requests import user_agent
from ..util import url_encode

PyCurl = pycurl.Curl


class ClosingCurl(closing):

    def __init__(self, curl_class):
        self._curl = curl_class()
        super(ClosingCurl, self).__init__(self._curl)

    def __getattr__(self, item):
        return getattr(self._curl, item)


class PyCurlMulti(ClosingCurl):

    def __init__(self):
        super(PyCurlMulti, self).__init__(pycurl.CurlMulti)


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
            post = url_encode(post)

        curl.setopt(pycurl.POSTFIELDS, post)
    else:
        post = [(x, byte_string(y)) for x, y in post.iteritems()]
        curl.setopt(pycurl.HTTPPOST, post)


def set_proxy(curl, proxy):
    if proxy.type == "socks4":
        curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS4)
    elif proxy.type == "socks5":
        curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
    else:
        curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
    curl.setopt(pycurl.PROXY, proxy.address)
    curl.setopt(pycurl.PROXYPORT, proxy.port)
    if proxy.auth:
        curl.setopt(pycurl.PROXYUSERPWD, str("%s:%s" % (proxy.user, proxy.password)))


def set_interface(curl, interface):
    curl.setopt(pycurl.INTERFACE, interface)


def set_ipv6_resolve(curl):
    curl.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_WHATEVER)


def set_ipv4_resolve(curl):
    curl.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V4)


def set_auth(curl, auth):
    curl.setopt(pycurl.USERPWD, auth)


def set_low_speed_timeout(curl, timeout):
    curl.setopt(pycurl.LOW_SPEED_TIME, timeout)


def set_cookies(curl, cookie):
    curl.setopt(pycurl.COOKIELIST, cookie)


def clear_cookies(curl):
    set_cookies(curl, '')


def unset_cookie_files(curl):
    curl.setopt(pycurl.COOKIEFILE, '')
    curl.setopt(pycurl.COOKIEJAR, '')


def set_url(curl, url):
    curl.setopt(pycurl.URL, url)


def set_referrer(curl, referrer):
    curl.setopt(pycurl.REFERER, referrer)


def set_headers(curl, headers):
    curl.setopt(pycurl.HTTPHEADER, headers)


def set_network_options(curl, interface=None, proxy=None, use_ipv6=False):
    if interface:
        set_interface(curl, str(interface))
    if proxy:
        set_proxy(curl, proxy)
    if use_ipv6:
        set_ipv6_resolve(curl)
    else:
        set_ipv4_resolve(curl)


def set_range(curl, bytes_range):
    curl.setopt(pycurl.RANGE, bytes_range)


def set_resume(curl, resume):
    curl.setopt(pycurl.RESUME_FROM, resume)


def set_body_header_fun(curl, body=None, header=None):
    if body:
        curl.setopt(pycurl.WRITEFUNCTION, body)
    if header:
        curl.setopt(pycurl.HEADERFUNCTION, header)


def perform_multi(curl):
    while True:
        ret, num_handles = curl.perform()
        if ret != pycurl.E_CALL_MULTI_PERFORM:
            break


def get_effective_url(curl):
    return curl.getinfo(pycurl.EFFECTIVE_URL)


def get_cookies(curl):
    return curl.getinfo(pycurl.INFO_COOKIELIST)


def get_status_code(curl):
    return int(curl.getinfo(pycurl.RESPONSE_CODE))
