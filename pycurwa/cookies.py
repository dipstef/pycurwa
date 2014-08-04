import urllib2


def get_cookie_string(cookie_jar, request):
    request = _urllib_request(request)

    cookie_jar.add_cookie_header(request)

    cookie = request.unredirected_hdrs.get('Cookie')
    return cookie


def _urllib_request(request):
    return urllib2.Request(request.url, headers=request.headers)


def write_cookies(cookie_jar, response):
    cookie_jar.extract_cookies(UrllibResponse(response), _urllib_request(response.request))


class UrllibResponse(object):

    def __init__(self, response):
        self.response = response

    def info(self):
        return self

    def getheaders(self, name):
        return self.response.headers.get_list(name)
