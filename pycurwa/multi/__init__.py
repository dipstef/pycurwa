from Queue import Queue
from threading import Thread

from httpy.client import cookie_jar

from pycurwa import PyCurwa
from pycurwa.multi.requests import LimitedRequests
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


class CurlMultiRequests(LimitedRequests):
    def __init__(self, max_connections, refresh=0.5):
        super(CurlMultiRequests, self).__init__(max_connections, refresh)
        self._updates = Queue()

        self._perform_thread = Thread(target=self.perform)
        self._perform_thread.start()

        self._update_thread = Thread(target=self._process_updates)
        self._update_thread.start()

    def perform(self):
        for status in self.iterate_statuses():
            self._updates.put(status)

    def _process_updates(self):
        while not self._is_closed():
            status = self._updates.get()
            if status:
                self._send_updates(status)

    def close(self, request):
        super(CurlMultiRequests, self).close(request)
        self._perform_thread.join()

        #unblocks the queue
        self._updates.put(None)
        self._update_thread.join()

        self._requests.stop()


def _send_updates(status):
    for request in status.completed:
        request.completed(status.time)
    for request in status.failed:
        request.failed(request.error)