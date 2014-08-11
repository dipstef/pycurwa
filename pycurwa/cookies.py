from cookielib import Cookie
import urllib2


class CurlCookies(object):

    def __init__(self, cookies):
        self._cookie_jar = cookies

    def add_cookies(self, cookie_list):
        for cookie_string in cookie_list:
            cookie = CurlCookie(cookie_string)
            self._cookie_jar.set_cookie(cookie)

    def get_cookie_string(self, request):
        request = urllib2.Request(request.url, headers=request.headers)

        self._cookie_jar.add_cookie_header(request)

        cookie = request.unredirected_hdrs.get('Cookie')
        return cookie

    def __repr__(self):
        return repr(self._cookie_jar._cookies)

    def __len__(self):
        return len(self._cookie_jar)


class CurlCookie(Cookie):
    def __init__(self, cookie_string):
        http_only_check = cookie_string.partition('#HttpOnly_')
        http_only = bool(http_only_check[1])

        if http_only:
            cookie_string = http_only_check[-1]

        domain, domain_initial_dot, path, secure, expiration, name, value = cookie_string.split('\t')

        domain_initial_dot = domain_initial_dot.lower() == 'true'
        secure = secure.lower() == 'true'

        rest = {'httponly': None} if http_only else {}

        expiration = int(expiration) or None

        Cookie.__init__(self, version=0, name=name, value=value, port=None, port_specified=False, domain=domain,
                        domain_specified=bool(domain), domain_initial_dot=domain_initial_dot,
                        path=path, path_specified=bool(path), secure=secure, expires=expiration,
                        discard=not expiration, comment=None, comment_url=None, rest=rest, rfc2109=False)