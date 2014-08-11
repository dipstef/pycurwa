from collections import OrderedDict
from itertools import groupby

from ...curl.requests import RequestsStatus
from ..requests import Requests, RequestsUpdates
from ...download import ChunksDownloads


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
        self._requests_handles = OrderedDict()

    def add(self, requests):
        handles = self._get_requests_handles(requests)

        for request in requests:
            self._handles_requests[request.handle] = requests
            handles.add(request.handle)

    def _get_requests_handles(self, requests):
        requests_handles = self._requests_handles.get(requests)
        if not requests_handles:
            requests_handles = set()
            self._requests_handles[requests] = requests_handles

        return requests_handles

    def close(self, requests):
        for request in requests:
            group = self._handles_requests[request.handle]
            del self._handles_requests[request.handle]

            handles = self._requests_handles[group]
            handles.remove(request.handle)

            if not handles:
                del self._requests_handles[group]

    def get_status(self, status):
        requests_status = RequestGroupStatus(self._requests_handles, status)

        for group, completed in self._group_by_requests(status.completed):
            requests_status.add_completed(group, completed)

        for group, failed in self._group_by_requests(status.failed):
            requests_status.add_failed(group, failed)

        return requests_status

    def _group_by_requests(self, requests):
        existing = (request for request in requests if request.handle in self._handles_requests)

        grouped = groupby(existing, key=lambda request: self._handles_requests[request.handle])
        return ((group, list(group_requests)) for group, group_requests in grouped)

    def __iter__(self):
        return self._requests_handles.iterkeys()

    def __len__(self):
        return len(self._requests_handles)


class DownloadRequests(RequestsUpdates):

    def __init__(self, max_connections=10, refresh=0.5):
        super(DownloadRequests, self).__init__(Requests(max_connections, refresh=refresh))
        self._multi = RequestGroups()

    def add(self, requests):
        self._multi.add(requests)
        for request in requests:
            self._requests.add(request)

    def _is_status_update(self, status):
        #always send updates
        return True

    def _send_updates(self, status):
        requests_status = self._multi.get_status(status)

        for requests, status in requests_status:
            requests.update(status)

    def close(self, requests):
        self._multi.close(requests)

        for request in requests:
            self._requests.close(request)


class ChunksMultiRequests(ChunksDownloads):

    def __init__(self, requests, chunks_file, cookies=None, bucket=None):
        super(ChunksMultiRequests, self).__init__(chunks_file, cookies, bucket)
        self._requests = requests

    def _submit(self):
        self._requests.add(self)

    def close(self):
        self._requests.close(self)