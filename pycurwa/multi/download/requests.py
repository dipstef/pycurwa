from collections import OrderedDict
from itertools import groupby

from ...curl.requests import RequestsStatus
from ...error import FailedStatus
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

    def get_status(self, status):
        requests_status = RequestGroupStatus(self._request_groups, status)

        for group, completed in groupby(status.completed, key=lambda r: self._handles_requests[r.handle]):
            requests_status.add_completed(group, list(completed))

        for group, failed in groupby(status.failed, key=lambda r: self._handles_requests[r.handle]):
            requests_status.add_failed(group, list(failed))

        return requests_status


class RequestGroupStatus(RequestsStatus):

    def __init__(self, requests, status):
        super(RequestGroupStatus, self).__init__([], [], status.check)
        self._status = status
        self._statuses = OrderedDict(((requests, RequestsStatus([], [], status.check)) for requests in requests))

    def add_completed(self, requests, completed):
        self._statuses[requests] = RequestsStatus(completed, [], self.check)
        self.completed.append(requests)

    def add_failed(self, requests, failed):
        self._statuses[requests] = RequestsStatus(self._get_completed(requests), failed, self.check)
        self.failed.append(requests)

    def _get_completed(self, requests):
        return self._statuses.get(requests).completed

    def __iter__(self):
        return self._statuses.iteritems()


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
        requests_status = self._multi.get_status(status)

        self._update_requests(requests_status)

    def _update_requests(self, requests_status):
        for requests, status in requests_status:
            try:
                requests.update(status)
            except FailedStatus:
                if not requests in requests_status.failed:
                    requests_status.failed.append(requests)

    def close(self, requests):
        self._multi.close(requests)