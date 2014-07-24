from time import time


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