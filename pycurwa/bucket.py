from threading import Lock
from time import time, sleep


class Bucket(object):
    def __init__(self, max_speed=0):
        self._speed_rate = max_speed
        self._tokens = 0
        self._last_transfer_time = time()
        self._lock = Lock()

    def set_max_speed(self, rate):
        with self._lock:
            self._speed_rate = int(rate)

    def sleep_if_above_rate(self, received):
        #min. 10kb, may become unresponsive otherwise
        if self._speed_rate >= 10240:
            with self._lock:

                if self._tokens < self._speed_rate:
                    now = time()
                    delta = self._speed_rate * (now - self._last_transfer_time)
                    self._tokens = min(self._speed_rate, self._tokens + delta)
                    self._last_transfer_time = now

                self._tokens -= received

                if self._tokens < 0:
                    seconds = -self._tokens/float(self._speed_rate)

                    if seconds > 0:
                        #print 'Sleeping: ', seconds
                        sleep(seconds)

    def __nonzero__(self):
        return not self._speed_rate < 10240