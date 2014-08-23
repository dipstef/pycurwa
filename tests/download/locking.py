import os
from threading import Thread
import time
from pycurwa.download.files import open_locked


def _test_locked(i):
    with open_locked('locking.txt', 'a') as fp:
        print 'writing:', i
        fp.write(unicode(i) + '\n')
        time.sleep(1)


def main():
    threads = []
    try:
        for i in range(1, 100):
            t = Thread(target=_test_locked, args=(i, ))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
    finally:
        os.remove('locking.txt')

if __name__ == '__main__':
    main()