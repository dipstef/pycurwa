from httpy.client import HttpClient
from httpy.client.requests import cookie_jar
from .cookies import CurlCookies
from .request import CurlRequest


class PyCurwa(HttpClient):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        super(PyCurwa, self).__init__(timeout)
        self._cookies = CurlCookies(cookies) if cookies is not None else None
        self._bucket = bucket

    def execute(self, request, **kwargs):
        request = CurlRequest(request, cookies=self._cookies, bucket=self._bucket)

        return request.execute()

pycurwa = PyCurwa()