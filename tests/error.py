from httpy import HttpRequest
from httpy.connection.error import NoRouteToHost
from httpy.error import HttpServerError, HttpServerSocketError
from pycurwa.curl.error import CurlHttpServerSocketError, PyCurlError

request = HttpRequest('GET', 'http://test.com')
error = CurlHttpServerSocketError(request, NoRouteToHost('No Route To Host'), 7, '')
assert isinstance(error, CurlHttpServerSocketError)
assert isinstance(error, HttpServerSocketError)
assert isinstance(error, HttpServerError)
assert isinstance(error, NoRouteToHost)
assert isinstance(error, PyCurlError)

#print error