from httpy import HttpRequest
from httpy.connection.error import NoRouteToHost, NotConnected
from httpy.error import HttpServerError, HttpServerSocketError, IncompleteRead
import pycurl
from pycurwa.curl.error import CurlHttpServerSocketError, PyCurlError, HttpCurlError, CurlNotConnected

request = HttpRequest('GET', 'http://test.com')
error = CurlHttpServerSocketError(request, NoRouteToHost('No Route To Host'), 7, '')
assert isinstance(error, CurlHttpServerSocketError)
assert isinstance(error, HttpServerSocketError)
assert isinstance(error, HttpServerError)
assert isinstance(error, NoRouteToHost)
assert isinstance(error, PyCurlError)

error = HttpCurlError(request, pycurl.E_PARTIAL_FILE, 'Foo', disconnected_check=False)
assert isinstance(error, IncompleteRead)
#print error

error = CurlNotConnected(request, pycurl.E_PARTIAL_FILE, 'Foo')
assert isinstance(error.curl_error, IncompleteRead)
assert isinstance(error, NotConnected)


error = HttpCurlError(request, pycurl.E_PARTIAL_FILE, 'Foo', disconnected_check=True)
assert isinstance(error.curl_error, IncompleteRead)
assert isinstance(error, NotConnected)
