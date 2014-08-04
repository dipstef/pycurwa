from pycurwa import pycurwa


def main():
    url = 'http://www.google.com'

    response = pycurwa.get(url)

    print response.read()

if __name__ == '__main__':
    main()