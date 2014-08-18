from collections import OrderedDict
from itertools import groupby
from procol.console import print_err_trace

from ..requests import Requests, RequestsUpdates
from ...curl.requests import RequestsStatus


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
        self._handles_group = OrderedDict()
        self._group_handles = OrderedDict()

    def add(self, request, group):
        handles = self._get_requests_handles(group)

        self._handles_group[request.handle] = group
        handles.add(request.handle)

    def _get_requests_handles(self, requests):
        requests_handles = self._group_handles.get(requests)
        if not requests_handles:
            requests_handles = set()
            self._group_handles[requests] = requests_handles

        return requests_handles

    def close(self, request):
        group = self._handles_group.get(request.handle)
        if group:
            del self._handles_group[request.handle]

            handles = self._group_handles[group]
            handles.remove(request.handle)

            if not handles:
                del self._group_handles[group]

    def get_status(self, status):
        requests_status = RequestGroupStatus(self._group_handles, status)

        for group, completed in self._group_by_requests(status.completed):
            requests_status.add_completed(group, completed)

        for group, failed in self._group_by_requests(status.failed):
            requests_status.add_failed(group, failed)

        return requests_status

    def _group_by_requests(self, requests):
        existing = (request for request in requests if request.handle in self._handles_group)

        grouped = groupby(existing, key=lambda request: self._handles_group[request.handle])
        return ((group, list(group_requests)) for group, group_requests in grouped)

    def group_by_requests(self, status):
        requests_status = self.get_status(status)

        for requests, status in requests_status:
            for request in status:
                self.close(request)

            yield requests, status

    def __iter__(self):
        return self._group_handles.iterkeys()

    def __len__(self):
        return len(self._group_handles)


class DownloadRequests(RequestsUpdates):

    def __init__(self, max_connections=10, refresh=0.5):
        super(DownloadRequests, self).__init__(Requests(max_connections, refresh=refresh))
        self._multi = RequestGroups()

    def add(self, requests):
        for request in requests:
            self._multi.add(request, requests)
            super(DownloadRequests, self).add(request)

    def _is_status_update(self, status):
        #always send updates
        return True

    def _send_updates(self, status):
        for requests, requests_status in self._multi.group_by_requests(status):
            try:
                requests.update(requests_status)
            except:
                #Should have been handled by the requests class
                print_err_trace()
                self.close(requests)

    def close(self, requests):
        for request in requests:
            self._multi.close(request)
            self._close(request)


class GroupRequest(object):

    def __init__(self, requests, request):
        self._requests = requests
        self._request = request
        self._submit()

    def _submit(self):
        self._requests.add(self)

    def update(self, status):
        if status.completed:
            self._completed()
        elif status.failed:
            self._failed(status.failed[0].error)

    def _completed(self):
        self._request.completed()

    def _failed(self, error):
        self._request.failed(error)

    def close(self):
        self._request.close()

    def __iter__(self):
        return iter([self._request])

    def __getattr__(self, item):
        return getattr(self._request, item)