from httpy.client import HttpClient
from httpy.client.requests import cookie_jar

from .request import CurlRequest
from .curl.cookies import CurlCookies
from .curl.bucket import TransferLimit


class PyCurwa(HttpClient):

    def __init__(self, cookies=cookie_jar, timeout=30):
        super(PyCurwa, self).__init__(timeout)
        self._cookies = CurlCookies(cookies) if cookies is not None else None
        self._bucket = TransferLimit(kbytes=0)

    def execute(self, request, **kwargs):
        request = CurlRequest(request, cookies=self._cookies, bucket=self._bucket)

        return request.execute()

    def set_speed(self, kbytes=None):
        self._bucket.max_speed = kbytes or 0

    def get_speed(self):
        return self._bucket and self._bucket.max_speed

pycurwa = PyCurwa()