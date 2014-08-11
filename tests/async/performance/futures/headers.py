from tests.async.performance.futures import request_times


def main():
    with request_times('HEAD', 'http://diskstation:5000', times=10000) as responses:
        for response in responses:
            print response.headers


if __name__ == '__main__':
    main()