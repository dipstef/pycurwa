from threading import Lock
from ..curl import CurlMulti


class CurlMultiThread(CurlMulti):

    def __init__(self):
        self._lock = Lock()
        super(CurlMultiThread, self).__init__()

    def add_handle(self, curl):
        with self._lock:
            super(CurlMultiThread, self).add_handle(curl)

    def remove_handle(self, curl):
        with self._lock:
            super(CurlMultiThread, self).remove_handle(curl)

    def execute(self):
        with self._lock:
            super(CurlMultiThread, self).execute()

    def get_status(self):
        with self._lock:
            return super(CurlMultiThread, self).get_status()

    def select(self, timeout=None):
        with self._lock:
            return super(CurlMultiThread, self).select(timeout)

    def close(self):
        with self._lock:
            return super(CurlMultiThread, self).close()