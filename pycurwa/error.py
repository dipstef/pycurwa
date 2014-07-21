from httplib import responses


class Abort(Exception):
    pass


bad_headers = range(400, 404) + range(405, 418) + range(500, 506)


class BadHeader(Exception):
    def __init__(self, code, content=""):
        Exception.__init__(self, "Bad server response: %s %s" % (code, responses[int(code)]))
        self.code = code
        self.content = content