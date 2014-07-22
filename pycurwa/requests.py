# -*- coding: utf-8 -*-

from threading import Lock

from urlo import get_domain

from pycurwa.bucket import Bucket
from pycurwa.request import CookieJar


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