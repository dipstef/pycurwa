from Queue import Queue
from httpy.client import cookie_jar

from .download import AsyncDownloadRequests, AsyncChunksDownloads
from ...curl.status import RequestsStatus


class DownloadGroups(AsyncDownloadRequests):

    def __init__(self, requests, cookies=cookie_jar, max_speed=None, timeout=30):
        super(DownloadGroups, self).__init__(ChunksDownloadGroup(requests), cookies, max_speed, timeout)

    def _create_download(self, request, **kwargs):
        downloads = AsyncDownloadsGroup(self._requests, request, self._cookies, self._bucket)
        return downloads

    def iterate_finished(self):
        return self._requests.iterate_finished()

    def _close(self):
        for _ in self.iterate_finished():
            pass


class AsyncDownloadsGroup(AsyncChunksDownloads):

    def __init__(self, group, request, cookies=None, bucket=None):
        super(AsyncDownloadsGroup, self).__init__(group, request, cookies, bucket)
        self.error = None

    def _download_failed(self, error):
        self._requests.failed(self, error)

    def _download_completed(self, status):
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