from collections import OrderedDict
from itertools import groupby
from httpy.error import HttpError

from ...curl.requests import RequestsStatus
from ..requests import Requests, RequestsUpdates


class RequestGroupStatus(object):

    def __init__(self, requests, status):
        self._status = status
        self._statuses = OrderedDict(((requests, RequestsStatus([], [], status.check)) for requests in requests))
        self.check = status.check
        self._completed = []
        self._failed = []

    def add_completed(self, requests, completed):
        self._statuses[requests] = RequestsStatus(completed, [], self.check)
        self._completed.append(requests)

    def add_failed(self, requests, failed):
        self._statuses[requests] = RequestsStatus(self._get_completed(requests), failed, self.check)
        self._failed.append(requests)

    def _get_completed(self, requests):
        return self._statuses.get(requests).completed

    @property
    def completed(self):
        return OrderedDict(((requests, self._statuses[requests]) for requests in self._completed))

    @property
    def failed(self):
        return OrderedDict(((requests, self._statuses[requests]) for requests in self._failed))

    def __iter__(self):
        return self._statuses.iteritems()


class RequestGroups(object):

    def __init__(self):
        super(RequestGroups, self).__init__()
        self._handles_requests = OrderedDict()
        self._request_groups = []

    def add(self, requests):
        for request in requests:
            self._handles_requests[request.handle] = requests

        if not requests in self._request_groups:
            self._request_groups.append(requests)

    def close(self, requests):
        for request in requests:
            del self._handles_requests[request.handle]

        self._request_groups.remove(requests)

    def get_status(self, status):
        requests_status = RequestGroupStatus(self._request_groups, status)

        for group, completed in groupby(status.completed, key=lambda r: self._handles_requests[r.handle]):
            requests_status.add_completed(group, list(completed))

        for group, failed in groupby(status.failed, key=lambda r: self._handles_requests[r.handle]):
            requests_status.add_failed(group, list(failed))

        return requests_status

    def __iter__(self):
        return iter(self._request_groups)

    def __len__(self):
        return len(self._request_groups)


class DownloadRequests(RequestsUpdates):

    def __init__(self, max_connections=10, refresh=0.5):
        super(DownloadRequests, self).__init__(Requests(max_connections, refresh=refresh))
        self._multi = RequestGroups()

    def add(self, requests):
        for request in requests:
            self._requests.add(request)

        self._multi.add(requests)

    def _is_status_update(self, status):
        #always send updates
        return True

    def _send_updates(self, status):
        requests_status = self._multi.get_status(status)

        self._update_requests(requests_status)

    def _update_requests(self, requests_status):
        for requests, status in requests_status:
            requests.update(status)

    def close(self, requests):
        for request in requests:
            self._requests.close(request)
        self._multi.close(requests)