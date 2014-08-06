from tests.multi.performance import request_times


def main():
    #don' try this at home, actually it holds fine
    with request_times('GET', 'http://diskstation:5000', times=10000) as responses:
        for response in responses:
            print response.body


if __name__ == '__main__':
    main()