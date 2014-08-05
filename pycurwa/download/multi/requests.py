from collections import OrderedDict
from itertools import groupby
from threading import Event, Thread
from Queue import Queue

from ...curl.requests import MultiRequestRefresh, RequestsStatus
from ...multi.requests import LimitedRequests


class MultiRequests(MultiRequestRefresh):

    def __init__(self, refresh=0.5, requests=None):
        super(MultiRequests, self).__init__(refresh, requests)
        self._request_groups = []

    def add(self, requests):
        super(MultiRequests, self).add(requests)

        if not requests in self._request_groups:
            self._request_groups.append(requests)

    def remove(self, requests):
        super(MultiRequests, self).remove(requests)
        self._request_groups.remove(requests)

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

        for group, completed in groupby(status.completed, key=lambda r: self._handles_requests[r.handle]):
            statuses[group] = RequestsStatus(list(completed), [], status.check)

        for group, failed in groupby(status.failed, key=lambda r: self._handles_requests[r.handle]):
            statuses[group] = RequestsStatus(statuses.get(group).completed, list(failed), status.check)

        return statuses.iteritems()


class DownloadRequests(MultiRequests):

    def __init__(self, max_connections=2, refresh=0.5):
        super(DownloadRequests, self).__init__(refresh, LimitedRequests(max_connections))
        self._closed = Event()
        self._updates = Queue()

        self._active_requests = Event()

        self._perform_thread = Thread(target=self.perform)
        self._perform_thread.start()

        self._update_thread = Thread(target=self._process_updates)
        self._update_thread.start()

    def add(self, requests):
        super(DownloadRequests, self).add(requests)
        self._active_requests.set()

    def remove(self, requests):
        super(DownloadRequests, self).remove(requests)
        if not self._requests:
            self._active_requests.clear()

    def iterate_statuses(self):
        return super(DownloadRequests, self).iterate_statuses()

    def _has_active_requests(self):
        if self._requests:
            return not self._is_closed()
        else:
            self._active_requests.wait()
            return not self._is_closed()

    def _is_closed(self):
        return self._closed.is_set()

    def _update_status(self, status):
        self._updates.put(status)

    def _process_updates(self):
        while not self._is_closed():
            status = self._updates.get()
            if status:
                super(DownloadRequests, self)._update_status(status)

    def close(self):
        self._closed.set()

        if not self._active_requests.is_set():
            self._active_requests.set()

        self._perform_thread.join()

        #unblocks the queue
        self._updates.put(None)
        self._update_thread.join()