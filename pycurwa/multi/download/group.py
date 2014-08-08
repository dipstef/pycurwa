from Queue import Queue

from httpy.client import cookie_jar

from . import ChunksMultiRequests
from ..download.requests import DownloadRequests
from ...download import HttpDownloadRequests
from ...curl.requests import RequestsStatus


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
        super(DownloadGroup, self)._update_requests(requests_status)

        completed = [group for group in requests_status.completed if len(group.completed) == len(group.chunks)]
        if completed or requests_status.failed:
            status = RequestsStatus(completed, requests_status.failed, requests_status.check)
            self._outcome.put(status)