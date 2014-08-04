import pycurl
from httpy.client import user_agent
from unicoder import byte_string
from urllib import urlencode
from urlo import params_url

_default_headers = ['Accept: */*',
                    'Accept-Language: en-US,en',
                    'Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                    'Connection: keep-alive',
                    'Keep-Alive: 300', 'Expect:']


def _curl_request(curl, verbose=False, redirect=True):
    curl.setopt(pycurl.FOLLOWLOCATION, int(redirect))
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


def curl_request(curl, request, referrer=None, params=None, multi_part=False):
    _curl_request(curl)

    url = byte_string(request.url)

    url = params_url(url, urlencode(params)) if params else url

    curl.set_url(url)

    if request.method.lower() == 'head':
        curl.headers_only()

    if request.data:
        _post_request(curl, request.data, multi_part)
    else:
        curl.setopt(pycurl.POST, 0)

    if referrer:
        curl.set_referrer(referrer)


def _post_request(curl, post, multi_part=False):
    curl.setopt(pycurl.POST, 1)

    if not multi_part:
        if type(post) == unicode:
            post = byte_string(post)
        elif not type(post) == str:
            post = _url_encode(post)

        curl.setopt(pycurl.POSTFIELDS, post)
    else:
        post = [(x, byte_string(y)) for x, y in post.iteritems()]
        curl.setopt(pycurl.HTTPPOST, post)


def _url_encode(data):
    data = dict(data)
    data = {byte_string(x): byte_string(y) for x, y in data.iteritems()}
    return urlencode(data)

