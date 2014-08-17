from threading import Lock
from time import time, sleep


class TransferLimit(object):
    def __init__(self, kbytes=0):
        self._speed_rate = 0
        self._tokens = 0
        self._last_transfer_time = time()
        self._lock = Lock()

        self.max_speed = kbytes

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

    @property
    def max_speed(self):
        return self._speed_rate

    @max_speed.setter
    def max_speed(self, kbytes):
        with self._lock:
            self._speed_rate = int(kbytes*1024)

    def __nonzero__(self):
        return not self._speed_rate < 10240