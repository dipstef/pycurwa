from collections import OrderedDict
from itertools import groupby

from ...curl.requests import RequestsStatus, MultiRequests
from ...multi.requests import Requests, RequestsUpdates


class DownloadMultiRequests(MultiRequests):

    def __init__(self, requests):
        super(DownloadMultiRequests, self).__init__(requests)
        self._request_groups = []

    def add(self, requests):
        super(DownloadMultiRequests, self).add(requests)

        if not requests in self._request_groups:
            self._request_groups.append(requests)

    def remove(self, requests):
        super(DownloadMultiRequests, self).remove(requests)
        self._request_groups.remove(requests)

    def perform(self):
        for status in self.iterate_statuses():
            self._send_updates(status)

    def _send_updates(self, status):
        for request, request_status in self._group_by_request(status):
            request.update(request_status)

    def _group_by_request(self, status):
        statuses = OrderedDict(((requests, RequestsStatus([], [], status.check)) for requests in self._request_groups))

        for group, completed in groupby(status.completed, key=lambda r: self._handles_requests[r.handle]):
            statuses[group] = RequestsStatus(list(completed), [], status.check)

        for group, failed in groupby(status.failed, key=lambda r: self._handles_requests[r.handle]):
            statuses[group] = RequestsStatus(statuses.get(group).completed, list(failed), status.check)

        return statuses.iteritems()


class DownloadRequests(RequestsUpdates):

    def __init__(self, max_connections=10, refresh=0.5):
        requests = Requests(max_connections, refresh=refresh)
        super(DownloadRequests, self).__init__(requests)

        self._multi = DownloadMultiRequests(requests)

    def add(self, requests):
        self._multi.add(requests)

    def remove(self, requets):
        self._multi.remove(requets)

    def _is_status_update(self, status):
        #always send updates
        return True

    def _send_updates(self, status):
        self._multi._send_updates(status)

    def close(self):
        self.stop()