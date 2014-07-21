from download import HTTPDownload
from request import HTTPRequest


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
        http = HTTPRequest(self._cookie_jar)
        result =  http.load(url, *args, **kwargs)

        self._last_url = url
        return result