from collections import OrderedDict
from itertools import groupby

from ...curl.requests import RequestsStatus
from ..requests import Requests, RequestsUpdates


class MultiRequests(object):

    def __init__(self, requests):
        self._requests = requests
        self._handles_requests = OrderedDict()

    def add(self, requests):
        for request in requests:
            self._requests.add(request)
            self._handles_requests[request.handle] = requests

    def close(self, requests):
        for request in requests:
            self._requests.close(request)
            del self._handles_requests[request.handle]

    def iterate_statuses(self):
        return self._requests.iterate_statuses()

    def stop(self):
        self._requests.stop()


class DownloadMultiRequests(MultiRequests):

    def __init__(self, requests):
        super(DownloadMultiRequests, self).__init__(requests)
        self._request_groups = []

    def add(self, requests):
        super(DownloadMultiRequests, self).add(requests)

        if not requests in self._request_groups:
            self._request_groups.append(requests)

    def close(self, requests):
        super(DownloadMultiRequests, self).close(requests)
        self._request_groups.remove(requests)

    def update(self, status):
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
        super(DownloadRequests, self).__init__(Requests(max_connections, refresh=refresh))
        self._multi = DownloadMultiRequests(self._requests)

    def add(self, requests):
        self._multi.add(requests)

    def _is_status_update(self, status):
        #always send updates
        return True

    def _send_updates(self, status):
        self._multi.update(status)

    def close(self, requests):
        self._multi.close(requests)