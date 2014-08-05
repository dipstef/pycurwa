from Queue import Queue

from httpy.client import cookie_jar

from pycurwa import PyCurwa
from pycurwa.request import CurlRequestBase
from pycurwa.response import CurlBodyResponse


class PyCurwaMulti(PyCurwa):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        super(PyCurwaMulti, self).__init__(cookies, bucket, timeout)
        self._requests = None

    def execute(self, request, **kwargs):
        return super(PyCurwaMulti, self).execute(request, **kwargs)


class CurlMultiRequest(CurlRequestBase):

    def __init__(self, request, cookies=None, bucket=None):
        super(CurlMultiRequest, self).__init__(request, cookies)
        self._outcome = Queue(1)
        self._response = CurlBodyResponse(self, cookies, bucket)

    def completed(self, completion):
        self._outcome.put(completion)
        self.close()

    def failed(self, error):
        self._outcome.put(error)
        self.close()

    def execute(self):
        outcome = self._outcome.get()

        if isinstance(outcome, BaseException):
            raise outcome

        return self._response