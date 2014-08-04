from time import time
import urllib2


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


def get_cookie_string(cookie_jar, request):
    request = _urllib_request(request)

    cookie_jar.add_cookie_header(request)

    cookie = request.unredirected_hdrs.get('Cookie')
    return cookie


def _urllib_request(request):
    return urllib2.Request(request.url, headers=request.headers)


def write_cookies(cookie_jar, response):
    cookie_jar.extract_cookies(UrllibResponse(response), _urllib_request(response.request))


class UrllibResponse(object):

    def __init__(self, response):
        self.response = response

    def info(self):
        return self

    def getheaders(self, name):
        return self.response.headers.get_list(name)
