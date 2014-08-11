from contextlib import contextmanager
from pycurwa.async import PyCurwaFutures


@contextmanager
def request_times(method, url, times):
    with PyCurwaFutures() as pycurwa:

        responses = []
        for i in range(1, times+1):
            print i
            response = pycurwa.request(method, url)
            responses.append(response)

        yield responses