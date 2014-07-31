from collections import OrderedDict
import itertools
from ..requests import MultiRequestRefresh, RequestsStatus


class MultiRequests(MultiRequestRefresh):

    def __init__(self, refresh=0.5):
        super(MultiRequests, self).__init__(refresh)
        self._request_groups = []

    def add(self, requests):
        super(MultiRequests, self).add(requests)
        if not requests in self._request_groups:
            self._request_groups.append(requests)

    def remove(self, requests):
        super(MultiRequests, self).remove(requests)
        self._request_groups.remove(requests)

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
