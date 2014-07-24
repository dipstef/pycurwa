from pycurwa.request import CurlRequests


def main():
    url = 'http://www.google.com'

    c = CurlRequests()
    print c.load(url)


if __name__ == '__main__':
    main()