from pycurwa.async import PyCurwaFutures


def main():
    with PyCurwaFutures() as pycurwa:
        response = pycurwa.get('http://download.thinkbroadband.com/not_found.zip')
        print response.status


if __name__ == '__main__':
    main()