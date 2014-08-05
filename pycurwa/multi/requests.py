from Queue import Queue
from threading import Event, Semaphore, Thread
from ..curl.requests import Requests
from ..download.multi.curl import CurlMultiThread


class LimitedRequests(Requests):

    def __init__(self, max_connections):
        self._closed = Event()

        self._handles_add = Queue()

        self._handles_count = Semaphore(max_connections)

        self._handles_thread = Thread(target=self._add_handles)
        self._handles_thread.start()

        super(LimitedRequests, self).__init__(curl=CurlMultiThread())

    def add(self, request):
        self._handles_add.put(request)

    def _add_handles(self):
        while not self._closed.is_set():
            request = self._handles_add.get()
            if request:
                self._handles_count.acquire()
                super(LimitedRequests, self).add(request)

    def terminate(self):
        self._closed.set()
        super(LimitedRequests, self).terminate()
        #unblocks the queue
        self._handles_add.put(None)
        self._handles_thread.join()

    def get_status(self):
        status = super(LimitedRequests, self).get_status()

        for _ in range(len(status.completed) + len(status.failed)):
            self._handles_count.release()

        return status