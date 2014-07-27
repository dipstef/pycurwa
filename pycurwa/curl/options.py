import pycurl
from urllib import urlencode
from unicoder import byte_string
from urlo import params_url
from ..util import url_encode


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

    def set_cookies(self, cookie):
        self.setopt(pycurl.COOKIELIST, cookie)

    def clear_cookies(self):
        self.unsetopt(self, pycurl.COOKIELIST)

    def unset_cookie_files(self):
        self.unsetopt(pycurl.COOKIEFILE, '')
        self.unsetopt(pycurl.COOKIEJAR, '')

    def set_url(self, url):
        self.setopt(pycurl.URL, url)

    def set_referrer(self, referrer):
        self.setopt(pycurl.REFERER, referrer)

    def set_headers(self, headers):
        self.setopt(pycurl.HTTPHEADER, headers)

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
            self.post_request(post_data, multi_part)
        else:
            self.unset_post()

        if referrer:
            self.set_referrer(referrer)

    def set_progress_function(self, fun):
        self.setopt(pycurl.PROGRESSFUNCTION, fun)

    def post_request(self, post, multi_part=False):
        self.set_post()

        if not multi_part:
            if type(post) == unicode:
                post = byte_string(post)
            elif not type(post) == str:
                post = url_encode(post)

            self.setopt(pycurl.POSTFIELDS, post)
        else:
            post = [(x, byte_string(y)) for x, y in post.iteritems()]
            self.setopt(pycurl.HTTPPOST, post)

    def set_post(self):
        self.setopt(pycurl.POST, 1)

    def unset_post(self):
        self.setopt(pycurl.POST, 0)


class GetOptions(object):

    def get_effective_url(self):
        return self.getinfo(pycurl.EFFECTIVE_URL)

    def get_cookies(self):
        return self.getinfo(pycurl.INFO_COOKIELIST)

    def get_status_code(self):
        return int(self.getinfo(pycurl.RESPONSE_CODE))

    def get_speed_download(self):
        return self.getinfo(pycurl.SPEED_DOWNLOAD)