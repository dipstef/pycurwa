from pycurwa import client


def main():
    url = 'http://www.google.com'

    response = client.get(url)

    print response.read()

if __name__ == '__main__':
    main()