from Queue import Queue

from httpy.client import cookie_jar

from .requests import AsyncChunksDownloads
from ...download import HttpDownloadRequests
from ...curl.requests import RequestsStatus


class GroupRequests(HttpDownloadRequests):

    def __init__(self, requests, cookies=cookie_jar, bucket=None, timeout=30):
        super(GroupRequests, self).__init__(cookies, bucket, timeout)
        self._group = ChunksDownloadGroup(requests)

    def _create_request(self, chunks_file, **kwargs):
        downloads = GroupMultiRequests(self._group, chunks_file, self._cookies, self._bucket)
        self._group.add(downloads)
        return downloads

    def iterate_finished(self):
        return self._group.iterate_finished()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        for _ in self.iterate_finished():
            pass


class GroupMultiRequests(AsyncChunksDownloads):
    def __init__(self, group, chunks_file, cookies=None, bucket=None):
        super(GroupMultiRequests, self).__init__(group, chunks_file, cookies, bucket)
        self.error = None

    def update(self, status):
        try:
            return super(GroupMultiRequests, self).update(status)
        except Exception, error:
            self.error = error
            self._requests.failed(self, status)

    def _done_downloading(self, status):
        super(GroupMultiRequests, self)._done_downloading(status)
        self._requests.downloaded(self, status)


class ChunksDownloadGroup(object):

    def __init__(self, requests):
        self._requests = requests

        self._outcome = Queue()
        self._remaining = 0

    def add(self, requests):
        self._remaining += 1
        self._requests.add(requests)

    def downloaded(self, requests, status):
        self._outcome.put(RequestsStatus(completed=[requests], failed=[], status_time=status.check))

    def failed(self, requests, status):
        self._outcome.put(RequestsStatus(completed=[], failed=[requests], status_time=status.check))

    def iterate_finished(self):
        while self._remaining:
            status = self._outcome.get()
            yield status

    def close(self, requests):
        self._remaining -= 1
        self._requests.close(requests)

    def __len__(self):
        return self._remaining