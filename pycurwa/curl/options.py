from collections import namedtuple
import pycurl


class SetOptions(object):

    def set_network_options(self, interface=None, proxy=None, use_ipv6=False):
        if interface:
            self.set_interface(interface)
        if proxy:
            self.set_proxy(proxy)
        if use_ipv6:
            self.set_ipv6_resolve()
        else:
            self.set_ipv4_resolve()

    def set_proxy(self, proxy):
        if proxy.is_socks4():
            self._set(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS4)
        elif proxy.is_socks5():
            self._set(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
        else:
            self._set(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)

        self._set(pycurl.PROXY, proxy.address)
        self._set(pycurl.PROXYPORT, proxy.port)
        if proxy.auth:
            self._set(pycurl.PROXYUSERPWD, str('%s:%s' % (proxy.user, proxy.password)))

    def set_interface(self, interface):
        self._set(pycurl.INTERFACE, interface)

    def set_ipv6_resolve(self):
        self._set(pycurl.IPRESOLVE, pycurl.IPRESOLVE_WHATEVER)

    def set_ipv4_resolve(self):
        self._set(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V4)

    def set_auth(self, auth):
        self._set(pycurl.USERPWD, auth)

    def set_low_speed_timeout(self, timeout):
        self._set(pycurl.LOW_SPEED_TIME, timeout)

    def set_cookie(self, cookie):
        self._set(pycurl.COOKIE, cookie)

    def set_cookie_list(self, cookie):
        self._set(pycurl.COOKIELIST, cookie)

    def set_url(self, url):
        self._set(pycurl.URL, url)

    def set_method(self, method):
        self._set(pycurl.CUSTOMREQUEST, method)

    def set_referrer(self, referrer):
        self._set(pycurl.REFERER, referrer)

    def set_headers(self, headers):
        self._set(pycurl.HTTPHEADER, headers)

    def set_range(self, start, end=None):
        bytes_range = '%i-%i' % (start, end) if end else '%i-' % start
        self._set(pycurl.RANGE, bytes_range)

    def set_resume(self, resume):
        self._set(pycurl.RESUME_FROM, resume)

    def set_body_fun(self, body):
        self._set(pycurl.WRITEFUNCTION, body)

    def set_header_fun(self, header_fun):
        self._set(pycurl.HEADERFUNCTION, header_fun)

    def set_progress_function(self, fun):
        self._set(pycurl.PROGRESSFUNCTION, fun)

    def headers_only(self):
        self._set(pycurl.NOBODY, 1)

    def enable_body_retrieve(self):
        self._set(pycurl.NOBODY, 0)

    def _set(self, name, value):
        self.setopt(name, value)


class GetOptions(object):

    def get_response_url(self):
        return self._get(pycurl.EFFECTIVE_URL)

    def get_cookies(self):
        return self._get(pycurl.INFO_COOKIELIST)

    def get_status_code(self):
        return int(self._get(pycurl.RESPONSE_CODE))

    def get_speed_download(self):
        return self._get(pycurl.SPEED_DOWNLOAD)

    def _get(self, name):
        return self.getinfo(name)


class Auth(namedtuple('Auth', ['user', 'password'])):
    def __new__(cls, user, password):
        return super(Auth, cls).__new__(cls, user, password)


class Proxy(namedtuple('Proxy', ['type', 'address', 'port', 'auth'])):

    def __new__(cls, proxy_type, address, port, auth=None):
        return super(Proxy, cls).__new__(cls, proxy_type, address, port, auth)

    def is_socks4(self):
        return self.type == 'socks4'

    def is_socks5(self):
        return self.type == 'socks5'