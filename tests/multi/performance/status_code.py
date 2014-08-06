from tests.multi.performance import request_times


def main():
    with request_times('HEAD', 'http://diskstation:5000', times=10000) as responses:
        for response in responses:
            print response.get_status_code()


if __name__ == '__main__':
    main()