from Queue import Queue
from threading import Event, Semaphore, Thread

from ..curl.requests import RequestRefresh
from ..download.multi.curl import CurlMultiThread


class LimitedRequests(RequestRefresh):

    def __init__(self, max_connections, refresh=0.5):
        self._closed = Event()

        self._handles_add = Queue()

        self._active_requests = Event()

        self._handles_count = Semaphore(max_connections)

        self._handles_thread = Thread(target=self._add_handles)
        self._handles_thread.start()

        super(LimitedRequests, self).__init__(refresh, curl=CurlMultiThread())

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
        self._active_requests.set()

    def remove(self, request):
        super(LimitedRequests, self).remove(request)
        if not self._requests:
            self._active_requests.clear()

    def stop(self):
        self._closed.set()
        if not self._active_requests.is_set():
            self._active_requests.set()

        super(LimitedRequests, self).stop()

        #unblocks the queue
        self._handles_add.put(None)
        self._handles_thread.join()

    def get_status(self):
        status = super(LimitedRequests, self).get_status()

        for _ in range(len(status.completed) + len(status.failed)):
            self._handles_count.release()

        return status

    def _has_active_requests(self):
        if self._requests:
            return not self._is_closed()
        else:
            self._active_requests.wait()
            return not self._is_closed()

    def _is_closed(self):
        return self._closed.is_set()
