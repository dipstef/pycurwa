from contextlib import contextmanager
from time import time

from . import CurlMulti
from .status import CurlRequests, RequestsStatus
from .error import CurlError


class Requests(CurlRequests):

    def __init__(self, curl=None):
        super(Requests, self).__init__(curl or CurlMulti())

    def add(self, request):
        self._requests[request.handle] = request
        self._add_curl_handle(request)

    def _add_curl_handle(self, request):
        try:
            self._curl.add_handle(request.handle)
        except CurlError:
            #already added
            pass

    def close(self, request):
        try:
            self._curl.remove_handle(request.handle)
            self._remove(request)
        except (CurlError, KeyError):
            #already removed
            pass

    def _remove(self, request):
        del self._requests[request.handle]
        request.close()

    @contextmanager
    def _curl_status(self):
        self._curl.execute()
        yield self._get_status(time())
        self._select(timeout=1)

    def iterate_statuses(self):
        try:
            while self._has_requests():
                with self._curl_status() as status:
                    yield status
        finally:
            self._terminate()

    def _select(self, timeout=1):
        self._curl.select(timeout)

    def _terminate(self):
        self._curl.close()

    def stop(self):
        self._terminate()

    def _has_requests(self):
        return bool(self._requests)

    def __contains__(self, handle):
        return handle in self._requests

    def __len__(self):
        return len(self._requests)

    def __iter__(self):
        return iter(self._requests.values())


class RequestsRefresh(Requests):

    def __init__(self, refresh=0.5, curl=None):
        super(RequestsRefresh, self).__init__(curl)
        self._refresh_rate = refresh
        self._last_update = 0

    def _get_status(self, now):
        if now - self._last_update >= self._refresh_rate:
            status = super(RequestsRefresh, self)._get_status(now)
            self._last_update = now
        else:
            status = RequestsStatus([], [], now)

        return status