from pycurwa.multi import PyCurwaMulti


def main():
    pycurwa = PyCurwaMulti()

    try:
        response = pycurwa.get('http://www.google.com')

        print response.read()
    finally:
        pycurwa.close()

if __name__ == '__main__':
    main()