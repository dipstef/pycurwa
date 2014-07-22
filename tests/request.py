from pycurwa.request import HTTPRequest


def main():
    url = 'http://www.google.com'

    c = HTTPRequest()
    print c.load(url)


if __name__ == '__main__':
    main()