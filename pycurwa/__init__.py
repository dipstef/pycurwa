from httpy.client import HttpClient
from httpy.client.requests import cookie_jar
from .request import CurlRequest


class PyCurwa(HttpClient):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        super(PyCurwa, self).__init__(timeout)
        self._cookies = cookies
        self._bucket = bucket

    def execute(self, request, **kwargs):
        request = CurlRequest(request, cookies=self._cookies, bucket=self._bucket)

        return request.execute()

pycurwa = PyCurwa()