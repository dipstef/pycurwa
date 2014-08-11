from threading import Lock
from .. import curl


class CurlMulti(curl.CurlMulti):

    def __init__(self):
        self._lock = Lock()
        super(CurlMulti, self).__init__()

    def add_handle(self, handle):
        with self._lock:
            super(CurlMulti, self).add_handle(handle)

    def remove_handle(self, handle):
        with self._lock:
            super(CurlMulti, self).remove_handle(handle)

    def execute(self):
        with self._lock:
            super(CurlMulti, self).execute()

    def get_status(self):
        with self._lock:
            return super(CurlMulti, self).get_status()

    def select(self, timeout=None):
        with self._lock:
            return super(CurlMulti, self).select(timeout)

    def close(self):
        with self._lock:
            return super(CurlMulti, self).close()