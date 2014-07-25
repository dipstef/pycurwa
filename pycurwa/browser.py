from threading import Lock
from urlo import get_domain
from download import HTTPDownload
from pycurwa.bucket import Bucket
from pycurwa.cookies import CookieJar
from request import CurlRequests


class Browser(object):
    __slots__ = ("log", "options", "bucket", "_cookie_jar", "_last_url")

    def __init__(self, cookie_jar=None, bucket=None):
        self.bucket = bucket

        self._cookie_jar = cookie_jar
        self._last_url = None

    def clear_cookies(self):
        if self._cookie_jar:
            self._cookie_jar.clear()

    def http_download(self, url, filename, get={}, post={}, ref=True, cookies=True, chunks=1, resume=False,
                     progressNotify=None, disposition=False):
        """ this can also download ftp """
        referrer = self._last_url if ref else None
        cookies = self._cookie_jar if cookies else None

        dl = HTTPDownload(url, filename, get, post, referrer, cookies, self.bucket, progressNotify, disposition)
        name = dl.download(chunks, resume)

        return name

    def load(self, url, *args, **kwargs):
        """ retrieves page """
        http = CurlRequests(self._cookie_jar)
        result = http.load(url, *args, **kwargs)

        self._last_url = url
        return result


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