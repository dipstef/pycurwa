import pycurl
import sys
import itertools

from .error import PyCurlError
from .options import SetOptions, GetOptions


py3 = sys.version_info[0] == 3

if py3:
    from io import BytesIO
else:
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO


class ClosingCurl(SetOptions, GetOptions):

    def __init__(self, curl_class):
        self.handle = curl_class()
        self.closed = False

    def close(self):
        self.handle.close()
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __eq__(self, other):
        return other == self.handle

    def __getattr__(self, item):
        return getattr(self.handle, item)


class CurlMulti(ClosingCurl):

    def __init__(self):
        super(CurlMulti, self).__init__(pycurl.CurlMulti)

    def add_handle(self, curl):
        if isinstance(curl, Curl):
            curl = curl.handle

        self.handle.add_handle(curl)

    def remove_handle(self, curl):
        if isinstance(curl, Curl):
            curl = curl.handle
        self.handle.remove_handle(curl)

    def execute(self):
        while True:
            ret, num_handles = self.handle.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

    def select(self, timeout=None):
        return self.handle.select(timeout)

    def get_status(self):
        remaining, completed, failed = self.handle.info_read()
        return CurlMultiStatus(completed, failed, remaining)


class CurlHandlesStatus(object):

    def __init__(self, completed=(), failed=()):
        self.completed = completed
        self.failed = failed

    def __iter__(self):
        return itertools.chain(self.completed, self.failed)


class CurlMultiStatus(CurlHandlesStatus):
    def __init__(self, completed, failed, remaining):
        super(CurlMultiStatus, self).__init__(completed, failed)
        self.remaining = remaining


class Curl(ClosingCurl):

    def __init__(self, proxy=None, interface=None, use_ipv6=False):
        super(Curl, self).__init__(pycurl.Curl)

        self.set_network_options(proxy, interface, use_ipv6)

    def perform(self):
        try:
            self.handle.perform()
        except pycurl.error, e:
            raise PyCurlError(*e.args)