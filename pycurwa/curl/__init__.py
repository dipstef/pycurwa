from contextlib import closing
import pycurl
import sys
from httpy.client.requests import user_agent
from .error import PyCurlError, CurlError
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


class Curl(ClosingCurl):

    def __init__(self, proxy=None, interface=None, use_ipv6=False):
        super(Curl, self).__init__(pycurl.Curl)

        self.set_network_options(proxy, interface, use_ipv6)

    def perform(self):
        try:
            self.curl.perform()
        except PyCurlError, e:
            raise CurlError(*e.args)


_default_headers = ['Accept: */*',
                    'Accept-Language: en-US,en',
                    'Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                    'Connection: keep-alive',
                    'Keep-Alive: 300', 'Expect:']


def curl_request(curl, verbose=False):
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.MAXREDIRS, 5)

    curl.setopt(pycurl.CONNECTTIMEOUT, 30)
    curl.setopt(pycurl.NOSIGNAL, 1)
    curl.setopt(pycurl.NOPROGRESS, 1)

    if hasattr(pycurl, 'AUTOREFERER'):
        curl.setopt(pycurl.AUTOREFERER, 1)

    curl.setopt(pycurl.SSL_VERIFYPEER, 0)

    curl.setopt(pycurl.LOW_SPEED_TIME, 30)
    curl.setopt(pycurl.LOW_SPEED_LIMIT, 5)

    if verbose:
        curl.setopt(pycurl.VERBOSE, 1)

    curl.setopt(pycurl.USERAGENT, user_agent)

    if pycurl.version_info()[7]:
        curl.setopt(pycurl.ENCODING, 'gzip, deflate')

    curl.setopt(pycurl.HTTPHEADER, _default_headers)