from httpy.client import HttpyRequest

from pycurwa import CurlRequest
from pycurwa.multi.requests import ProcessRequests


class Request(CurlRequest):
    def __init__(self, request, number, cookies=None, bucket=None):
        super(Request, self).__init__(request, cookies, bucket)
        self.number = number


def main():
    request = HttpyRequest('GET', 'http://diskstation:5000')

    requests = (Request(request, i+1) for i in range(0, 10000))

    with ProcessRequests(requests, max_connections=None) as requests:
        for status in requests.iterate_statuses():
            for request in status.completed:
                print request.number

if __name__ == '__main__':
    main()