from collections import OrderedDict
import itertools
from threading import Event, Lock, Thread
from pycurwa.requests import MultiRequestRefresh, RequestsStatus


class DownloadRequests(MultiRequestRefresh):

    def __init__(self, refresh=0.5):
        super(DownloadRequests, self).__init__(refresh)
        self._closed = Event()
        self._lock = Lock()

        self._thread = Thread(target=self.perform)
        self._thread.start()

    def add(self, requests):
        with self._lock:
            super(DownloadRequests, self).add(requests)

    def remove(self, requests):
        with self._lock:
            super(DownloadRequests, self).remove(requests)

    def _get_status(self):
        with self._lock:
            return super(DownloadRequests, self)._get_status()

    def perform(self):
        for _ in self.iterate_updates():
            pass

    def iterate_updates(self):
        for status in self.iterate_statuses():
            self._update_status(status)
            yield status

    def iterate_completed(self):
        for status in self.iterate_updates():
            for request in status.completed:
                yield request

    def _update_status(self, status):
        for request, request_status in self._group_by_request(status):
            request.update(request_status)

    def _group_by_request(self, status):
        statuses = OrderedDict(((requests, RequestsStatus([], [], status.check)) for requests in self._request_groups))

        for group, completed in itertools.groupby(status.completed, key=lambda r: self._handles_requests[r.handle]):
            statuses[group] = RequestsStatus(list(completed), [], status.check)

        for group, failed in itertools.groupby(status.failed, key=lambda r: self._handles_requests[r.handle]):
            statuses[group] = RequestsStatus(statuses.get(group).completed, list(failed), status.check)

        return statuses.iteritems()

    def _done(self):
        return self._closed.is_set()

    def close(self):
        self._closed.set()
        self._thread.join()