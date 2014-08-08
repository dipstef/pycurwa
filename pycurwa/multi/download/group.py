from Queue import Queue

from httpy.client import cookie_jar

from .requests import ChunksMultiRequests
from ..download.requests import RequestGroups
from ...download import HttpDownloadRequests
from ...curl.requests import RequestsStatus
from ...error import FailedStatus


class GroupRequests(HttpDownloadRequests):

    def __init__(self, requests, cookies=cookie_jar, bucket=None, timeout=30):
        super(GroupRequests, self).__init__(cookies, bucket, timeout)
        self._group = ChunksDownloadGroup(requests)
        self._requests = []

    def _create_request(self, chunks_file):
        downloads = GroupMultiRequests(self._group, chunks_file, self._cookies, self._bucket)

        self._requests.append(downloads)
        return downloads

    def submit(self):
        return self._group.add(self._requests)


class GroupMultiRequests(ChunksMultiRequests):
    def __init__(self, group, chunks_file, cookies=None, bucket=None):
        super(GroupMultiRequests, self).__init__(group, chunks_file, cookies, bucket)

    def downloaded(self):
        return self._completed


class ChunksDownloadGroup(object):

    def __init__(self, requests):
        self._groups = RequestGroups()
        self._requests = requests

    def add(self, groups):
        for requests in groups:
            self._groups.add(requests)

        group = GroupUpdate(self._groups)

        self._requests.add(group)
        return group

    def close(self, requests):
        self._groups.close(requests)
        self._requests.close(requests)

    def __len__(self):
        return len(self._groups)


class GroupUpdate(object):

    def __init__(self, groups):
        self._outcome = Queue()
        self._groups = groups

    def update(self, status):
        requests_status = self._groups.get_status(status)

        completed, failed = [], []

        for requests, status in requests_status:
            try:
                requests.update(status)
                if status.completed and requests.downloaded():
                    completed.append(requests)
            except FailedStatus:
                failed.append(requests)

        if completed or failed:
            self._outcome.put(RequestsStatus(completed, failed, requests_status.check))

    def iterate_finished(self):
        while self._groups:
            status = self._outcome.get()
            yield status

    def __iter__(self):
        return (request for requests in self._groups for request in requests)
