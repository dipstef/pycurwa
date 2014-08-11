from pycurwa.async import PyCurwaFutures


def main():
    with PyCurwaFutures() as pycurwa:

        response1 = pycurwa.get('http://www.google.com')
        response2 = pycurwa.get('http://www.twitter.com')
        response3 = pycurwa.get('http://www.facebook.com')
        response4 = pycurwa.get('http://www.apple.com')
        response5 = pycurwa.get('http://www.gibson.com')
        response6 = pycurwa.get('http://www.fender.com')

        print response1.url, response1.status
        print response2.url, response2.status
        print response3.url, response3.status
        print response4.url, response4.status
        print response5.url, response5.status
        print response6.url, response6.status

if __name__ == '__main__':
    main()