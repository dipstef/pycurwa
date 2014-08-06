from pycurwa.multi import PyCurwaMulti


def main():
    pycurwa = PyCurwaMulti()

    responses = []
    try:
        for i in range(1, 100):
            print i
            response = pycurwa.head('http://diskstation.local:5000')
            responses.append(response)

        for response in responses:
            print response.get_status_code()
    finally:
        pycurwa.close()

if __name__ == '__main__':
    main()