from Queue import Queue
from abc import abstractmethod
from threading import Event, Semaphore, Thread

from .curl import CurlMulti
from ..curl.requests import RequestsRefresh
from ..curl.error import CurlError


class RequestsProcess(RequestsRefresh):

    def __init__(self, refresh=0.5, curl=None):
        self._closed = Event()

        self._on_going_requests = Event()

        super(RequestsProcess, self).__init__(refresh, curl)

    def _has_requests(self):
        if self._requests:
            return not self.is_closed()
        else:
            self._on_going_requests.wait()
            return not self.is_closed()

    def is_closed(self):
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
            if not self.is_closed():
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


class RequestsStatuses(object):
    def __init__(self, requests):
        self._requests = requests
        self._updates = Queue()

    def perform(self):
        for status in self._requests.iterate_statuses():
            if self._is_status_update(status):
                self._updates.put(status)

    def _is_status_update(self, status):
        return True

    def iterate_statuses(self):
        while not self._requests.is_closed():
            status = self._updates.get()
            if status:
                yield status

    def stop(self):
        self._requests.stop()
        #unblocks the queue
        self._updates.put(None)


class RequestsUpdates(RequestsStatuses):

    def __init__(self, requests):
        super(RequestsUpdates, self).__init__(requests)

        self._perform_thread = Thread(target=self.perform)
        self._perform_thread.start()

        self._update_thread = Thread(target=self._process_updates)
        self._update_thread.start()

    def _process_updates(self):
        for status in self.iterate_statuses():
            self._send_updates(status)

    @abstractmethod
    def _send_updates(self, status):
        raise NotImplementedError

    def stop(self):
        super(RequestsUpdates, self).stop()
        self._perform_thread.join()
        self._update_thread.join()
