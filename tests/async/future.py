from pycurwa.async import PyCurwaFutures


def main():
    pycurwa = PyCurwaFutures()

    try:
        response1 = pycurwa.get('http://www.google.com')
        response2 = pycurwa.get('http://www.twitter.com')
        response3 = pycurwa.get('http://www.facebook.com')
        response4 = pycurwa.get('http://www.apple.com')
        response5 = pycurwa.get('http://www.gibson.com')
        response6 = pycurwa.get('http://www.fender.com')

        print response1.read()
        print response2.read()
        print response3.read()
        print response4.read()
        print response5.read()
        print response6.read()
    finally:
        pycurwa.close()

if __name__ == '__main__':
    main()