from Queue import Queue
from threading import Event, Semaphore, Thread

from .curl import CurlMulti
from ..curl.requests import RequestRefresh
from pycurwa.curl import CurlError


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
        self._closed.set()

        self._close()

        super(RequestsProcess, self)._terminate()

    def _close(self):
        #unblocks thread waiting for requests
        self._on_going_requests.set()

    def _select(self, timeout=1):
        try:
            super(RequestsProcess, self)._select(timeout)
        except CurlError:
            #might happen when requests a close meanwhile a status has been yielded, followed by the _select call
            #We simply ignore this case rather than checking on flag in each iteration
            if not self._is_closed():
                raise


class LimitedRequests(RequestsProcess):

    def __init__(self, max_connections, refresh=0.5):
        super(LimitedRequests, self).__init__(refresh, CurlMulti())
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
                if not self._closed.is_set():
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

    def _close(self):
        super(LimitedRequests, self)._close()
        #unblocks semaphore
        for i in range(len(self._requests)):
            self._handles_count.release()
        #unblocks the queue
        self._handles_add.put(None)
        self._handles_thread.join()