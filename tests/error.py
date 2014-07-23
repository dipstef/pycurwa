from httpy import HttpRequest
from httpy.connection.error import NoRouteToHost
from httpy.error import HttpServerError
from pycurwa.curl.error import CurlHttpServerError, PyCurlError

error = CurlHttpServerError(HttpRequest('GET', 'http://test.com'), NoRouteToHost('No Route To Host'))
assert isinstance(error, HttpServerError)
assert isinstance(error, NoRouteToHost)
assert isinstance(error, PyCurlError)

#print error