from procol.console import print_err
from pycurwa.async import PyCurwaAsync


def _response_received(response):
    print response.url, response.status


def _request_failed(request, error):
    print_err(request.url, error)


def main():
    with PyCurwaAsync() as pycurwa:
        pycurwa.get('http://www.google.com', on_completion=_response_received, on_err=_request_failed)
        pycurwa.get('http://www.twitter.com', on_completion=_response_received, on_err=_request_failed)
        pycurwa.pause(complete=True)
        pycurwa.get('http://www.facebook.com', on_completion=_response_received, on_err=_request_failed)
        pycurwa.get('http://www.apple.com', on_completion=_response_received, on_err=_request_failed)
        pycurwa.get('http://www.gibson.com', on_completion=_response_received, on_err=_request_failed)
        pycurwa.get('http://www.fender.com', on_completion=_response_received, on_err=_request_failed)

if __name__ == '__main__':
    main()