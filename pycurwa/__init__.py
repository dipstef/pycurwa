from httpy.client.requests import HttpRequests, cookie_jar
from .request import CurlRequest


class PyCurwa(HttpRequests):

    def __init__(self, cookies=cookie_jar, bucket=None):
        self._cookies = cookies
        self._bucket = bucket

    def execute(self, request, **kwargs):
        request = CurlRequest(request, cookies=self._cookies, bucket=self._bucket)

        return request.execute()

client = PyCurwa()