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
            self.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS4)
        elif proxy.is_socks5():
            self.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
        else:
            self.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_HTTP)

        self.setopt(pycurl.PROXY, proxy.address)
        self.setopt(pycurl.PROXYPORT, proxy.port)
        if proxy.auth:
            self.setopt(pycurl.PROXYUSERPWD, str('%s:%s' % (proxy.user, proxy.password)))

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

    def set_cookie(self, cookie):
        self.setopt(pycurl.COOKIE, cookie)

    def set_cookie_list(self, cookie):
        self.setopt(pycurl.COOKIELIST, cookie)

    def clear_cookies(self):
        self.unsetopt(self, pycurl.COOKIELIST)

    def unset_cookie_files(self):
        self.setopt(pycurl.COOKIEFILE, '')
        self.setopt(pycurl.COOKIEJAR, '')

    def set_url(self, url):
        self.setopt(pycurl.URL, url)

    def set_method(self, method):
        self.setopt(pycurl.CUSTOMREQUEST, method)

    def set_referrer(self, referrer):
        self.setopt(pycurl.REFERER, referrer)

    def set_headers(self, headers):
        self.setopt(pycurl.HTTPHEADER, headers)

    def set_range(self, start, end=None):
        bytes_range = '%i-%i' % (start, end) if end else '%i-' % start
        self.setopt(pycurl.RANGE, bytes_range)

    def set_resume(self, resume):
        self.setopt(pycurl.RESUME_FROM, resume)

    def set_body_fun(self, body):
        self.setopt(pycurl.WRITEFUNCTION, body)

    def set_header_fun(self, header_fun):
        self.setopt(pycurl.HEADERFUNCTION, header_fun)

    def set_progress_function(self, fun):
        self.setopt(pycurl.PROGRESSFUNCTION, fun)

    def headers_only(self):
        self.setopt(pycurl.NOBODY, 1)

    def enable_body_retrieve(self):
        self.setopt(pycurl.NOBODY, 0)


class GetOptions(object):

    def get_response_url(self):
        return self.getinfo(pycurl.EFFECTIVE_URL)

    def get_cookies(self):
        return self.getinfo(pycurl.INFO_COOKIELIST)

    def get_status_code(self):
        return int(self.getinfo(pycurl.RESPONSE_CODE))

    def get_speed_download(self):
        return self.getinfo(pycurl.SPEED_DOWNLOAD)


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