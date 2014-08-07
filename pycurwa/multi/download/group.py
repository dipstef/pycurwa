from Queue import Queue
from ..download.requests import DownloadRequests


class DownloadGroup(DownloadRequests):

    def __init__(self, max_connections=10, refresh=0.5):
        super(DownloadGroup, self).__init__(max_connections, refresh)
        self._outcome = Queue(1)

    def perform(self):
        status = self._outcome.get()
        return status

    def _send_updates(self, status):
        super(DownloadGroup, self)._send_updates(status)
        if not self._requests:
            self._outcome.put(status)