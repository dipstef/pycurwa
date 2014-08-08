from Queue import Queue

from httpy.client import cookie_jar

from . import ChunksMultiRequests
from ..download.requests import DownloadRequests, RequestGroups
from ...download import HttpDownloadRequests, ChunksDownloads
from ...curl.requests import RequestsStatus
from pycurwa.error import FailedStatus


class GroupRequests(HttpDownloadRequests):

    def __init__(self, group, cookies=cookie_jar, bucket=None, timeout=30):
        super(GroupRequests, self).__init__(cookies, bucket, timeout)
        self._requests = group

    def _create_request(self, chunks_file):
        return ChunksMultiRequests(self._requests, chunks_file, self._cookies, self._bucket)

    def close(self):
        self._requests.stop()


class DownloadGroup(DownloadRequests):

    def __init__(self, max_connections=10, refresh=0.5):
        super(DownloadGroup, self).__init__(max_connections, refresh)
        self._outcome = Queue(1)

    def iterate_finished(self):
        while self._requests:
            status = self._outcome.get()
            yield status

    def _update_requests(self, requests_status):
        completed, failed = [], []

        for requests, status in requests_status:
            try:
                requests.update(status)
                if status.completed and len(requests.chunks) == len(requests.completed):
                    completed.append(requests)
            except FailedStatus:
                failed.append(requests)

        if completed or failed:
            self._outcome.put(RequestsStatus(completed, failed, requests_status.check))


class HttpDownloadGroup(HttpDownloadRequests):

    def _create_request(self, chunks_file):
        return ChunksDownloads()


class ChunksDownloadGroup(object):

    def __init__(self, requests):
        self._requests = RequestGroups()
        self._requests.add(requests)
        self._outcome = Queue(1)

    def submit(self, requests):
        pass

    def iterate_finished(self):
        while self._requests:
            status = self._outcome.get()
            yield status

    def update(self, status):
        requests_status = self._requests.get_status(status)

        completed, failed = [], []

        for requests, status in requests_status:
            try:
                requests.update(status)
                if status.completed and len(requests.chunks) == len(requests.completed):
                    completed.append(requests)
            except FailedStatus:
                failed.append(requests)

        if completed or failed:
            self._outcome.put(RequestsStatus(completed, failed, requests_status.check))

    def close(self):
        pass

    def __iter__(self):
        return (request for requests in self._requests for request in requests)