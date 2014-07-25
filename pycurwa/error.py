from httplib import responses


class Abort(Exception):
    pass


bad_headers = range(400, 404) + range(405, 418) + range(500, 506)


class BadHeader(Exception):
    def __init__(self, code, content=''):
        Exception.__init__(self, 'Bad server response: %s %s' % (code, responses[int(code)]))
        self.code = code
        self.content = content


class WrongFormat(Exception):
    pass


class UnexpectedContent(Exception):
    def __init__(self, path, actual, expected):
        message = 'Downloaded content %d different than expected %d on chunk %s. Try to reduce download connections.'
        message = message % (actual, expected, path)
        super(UnexpectedContent, self).__init__(message)


class FallbackToSingleConnection(Exception):
    def __init__(self, error):
        message = 'Download chunks failed, fallback to single connection | %s' % (str(error))
        super(FallbackToSingleConnection, self).__init__(message)
        self.message = message


class RangeNotSatisfiable(BadHeader):

    def __init__(self, url, file_path, bytes_range):
        super(RangeNotSatisfiable, self).__init__(416)
        self.message = 'Range not satisfiable: %s: %s: %s' % (url, file_path, str(bytes_range))