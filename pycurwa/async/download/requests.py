from abc import abstractmethod
from collections import OrderedDict
from itertools import groupby
from httpy.error import HttpError
from procol.console import print_err_trace

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
        self._handles_group = OrderedDict()
        self._group_handles = OrderedDict()

    def add(self, requests):
        handles = self._get_requests_handles(requests)

        for request in requests:
            self._handles_group[request.handle] = requests
            handles.add(request.handle)

    def _get_requests_handles(self, requests):
        requests_handles = self._group_handles.get(requests)
        if not requests_handles:
            requests_handles = set()
            self._group_handles[requests] = requests_handles

        return requests_handles

    def close(self, requests):
        for request in requests:
            self._close(request)

    def _close(self, request):
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

    def __iter__(self):
        return self._group_handles.iterkeys()

    def __len__(self):
        return len(self._group_handles)


class DownloadRequests(RequestsUpdates):

    def __init__(self, max_connections=10, refresh=0.5):
        super(DownloadRequests, self).__init__(Requests(max_connections, refresh=refresh))
        self._multi = RequestGroups()

    def add(self, requests):
        self._multi.add(requests)
        for request in requests:
            super(DownloadRequests, self).add(request)

    def _is_status_update(self, status):
        #always send updates
        return True

    def _send_updates(self, status):
        requests_status = self._multi.get_status(status)

        for requests, status in requests_status:
            try:
                requests.update(status)
            except:
                #Should have been handled by the requests class
                print_err_trace()
                self.close(requests)

    def close(self, requests):
        self._multi.close(requests)

        for request in requests:
            self._requests.close(request)


class AsyncChunksDownloads(ChunksDownloads):

    def __init__(self, requests, request, chunks, cookies=None, bucket=None):
        super(AsyncChunksDownloads, self).__init__(request, cookies, bucket)
        self._requests = requests

        try:
            self._create_chunks(chunks)
            #starts downloads right away
            self._submit()
        except HttpError, error:
            self._download_failed(error)

    def _submit(self):
        self._requests.add(self)

    def _update(self, status):
        try:
            return self._update_status(status)
        except BaseException, e:
            self._download_failed(e)

    def _update_status(self, status):
        return super(AsyncChunksDownloads, self)._update(status)

    def _done_downloading(self, status):
        super(AsyncChunksDownloads, self)._done_downloading(status)
        self._download_completed(status)

    @abstractmethod
    def _download_failed(self, error):
        raise NotImplementedError

    @abstractmethod
    def _download_completed(self, status):
        raise NotImplementedError

    def close(self):
        self._requests.close(self)
