from Queue import Queue
from threading import Event, Semaphore, Thread

from .curl import CurlMultiThread
from ..curl.requests import RequestRefresh


class RequestsProcess(RequestRefresh):

    def __init__(self, refresh=0.5, curl=None):
        self._closed = Event()

        self._on_going_requests = Event()

        super(RequestsProcess, self).__init__(refresh, curl)

    def _has_requests(self):
        if self._requests:
            return not self._is_closed()
        else:
            self._on_going_requests.wait()
            return not self._is_closed()

    def _is_closed(self):
        return self._closed.is_set()

    def _terminate(self):
        if not self._is_closed():
            self._closed.set()

        if not self._on_going_requests.is_set():
            self._on_going_requests.set()

        super(RequestsProcess, self)._terminate()


class LimitedRequests(RequestsProcess):

    def __init__(self, max_connections, refresh=0.5):
        super(LimitedRequests, self).__init__(refresh, CurlMultiThread())
        self._handles_add = Queue()
        self._handles_count = Semaphore(max_connections)

        self._handles_thread = Thread(target=self._add_handles)
        self._handles_thread.start()

    def add(self, request):
        self._handles_add.put(request)

    def _add_handles(self):
        while not self._closed.is_set():
            request = self._handles_add.get()
            if request:
                self._handles_count.acquire()
                self._add_request(request)

    def _add_request(self, request):
        super(LimitedRequests, self).add(request)
        self._on_going_requests.set()

    def remove(self, request):
        super(LimitedRequests, self).remove(request)
        if not self._requests:
            self._on_going_requests.clear()

    def get_status(self):
        status = super(LimitedRequests, self).get_status()

        for _ in range(len(status.completed) + len(status.failed)):
            self._handles_count.release()

        return status

    def _terminate(self):
        super(LimitedRequests, self)._terminate()
        #unblocks the queue
        self._handles_add.put(None)
        self._handles_thread.join()