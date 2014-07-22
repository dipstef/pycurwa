# -*- coding: utf-8 -*-

from threading import Lock
from time import time, sleep
from urlo import get_domain


class Bucket(object):
    def __init__(self, max_speed=0):
        self._speed_rate = max_speed
        self._tokens = 0
        self._last_transfer_time = time()
        self._lock = Lock()

    def set_max_speed(self, rate):
        with self._lock:
            self._speed_rate = int(rate)

    def sleep_above_rate(self, transferred):
        """ return time the process have to sleep, after consumed specified amount """
        #min. 10kb, may become unresponsive otherwise
        if self._speed_rate >= 10240:
            with self._lock:

                if self._tokens < self._speed_rate:
                    now = time()
                    delta = self._speed_rate * (now - self._last_transfer_time)
                    self._tokens = min(self._speed_rate, self._tokens + delta)
                    self._last_transfer_time = now

                self._tokens -= transferred

                if self._tokens < 0:
                    seconds = -self._tokens/float(self._speed_rate)

                    if seconds > 0:
                        print 'Sleeping: ', seconds
                        sleep(seconds)

    def __nonzero__(self):
        return False if self._speed_rate < 10240 else True


class RequestFactory(object):
    def __init__(self, max_speed=0):
        self._lock = Lock()
        self.bucket = Bucket(max_speed)
        self.bucket.set_max_speed(max_speed)
        self.cookie_jars = {}

    def get_request(self, url):
        domain = get_domain(url)
        with self._lock:
            from browser import Browser
            cookie_jar = self._get_cookie_jar(domain)
            req = Browser(cookie_jar, self.bucket)

        return req

    def _get_cookie_jar(self, domain):
        cookie_jar = self.cookie_jars.get(domain)
        if not cookie_jar:
            cookie_jar = CookieJar(domain)
            self.cookie_jars[domain] = cookie_jar
        return cookie_jar


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