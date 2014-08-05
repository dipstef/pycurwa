from contextlib import closing
import pycurl
import sys

from .error import CurlError
from .options import SetOptions, GetOptions


py3 = sys.version_info[0] == 3

if py3:
    from io import BytesIO
else:
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        from StringIO import StringIO as BytesIO


class ClosingCurl(closing, SetOptions, GetOptions):

    def __init__(self, curl_class):
        self.curl = curl_class()
        super(ClosingCurl, self).__init__(self)

    def __eq__(self, other):
        return other == self.curl

    def __getattr__(self, item):
        return getattr(self.curl, item)


class CurlMulti(ClosingCurl):

    def __init__(self):
        super(CurlMulti, self).__init__(pycurl.CurlMulti)

    def add_handle(self, curl):
        if isinstance(curl, Curl):
            curl = curl.curl

        self.curl.add_handle(curl)

    def remove_handle(self, curl):
        if isinstance(curl, Curl):
            curl = curl.curl
        self.curl.remove_handle(curl)

    def execute(self):
        while True:
            ret, num_handles = self.curl.perform()
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break

    def select(self, timeout=None):
        return self.curl.select(timeout)

    def get_status(self):
        remaining, completed, failed = self.curl.info_read()
        return CurlMultiStatus(completed, failed, remaining)

    def close(self):
        self.curl.close()


class CurlHandlesStatus(object):

    def __init__(self, completed=(), failed=()):
        self.completed = completed
        self.failed = failed


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
            self.curl.perform()
        except pycurl.error, e:
            raise CurlError(*e.args)