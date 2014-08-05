from httpy.client import cookie_jar
from pycurwa import PyCurwa


class PyCurwaMulti(PyCurwa):

    def __init__(self, cookies=cookie_jar, bucket=None, timeout=30):
        super(PyCurwaMulti, self).__init__(cookies, bucket, timeout)
        self._requests = None