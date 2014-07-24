import numbers
import operator


class Tuple(tuple):

    def __new__(cls, seq=()):
        return super(Tuple, cls).__new__(cls, seq)

    def __add__(self, other):
        return self._zip_op(operator.add, other, default=0)

    def __sub__(self, other):
        return self._zip_op(operator.sub, other, default=0)

    def __mul__(self, other):
        return self._zip_tuple_or_number(operator.mul, other, default=1)

    def __div__(self, other):
        return self._zip_tuple_or_number(operator.div, other, default=1)

    def _zip_tuple_or_number(self, op, other, default=1):
        if isinstance(other, numbers.Number):
            other = (other, ) * len(self)
        return self._zip_op(op, other, default=default)

    def _zip_op(self, op, other, default=0):
        length_diff = len(self) - len(other)
        current = self
        if length_diff > 0:
            other = tuple(other) + (default, ) * length_diff
        elif length_diff < 0:
            current = tuple(self) + (default, ) * -length_diff
        return self.__class__(op(*zip_tuple) for zip_tuple in zip(current, other))

    def sum(self):
        return sum(self)


class DownloadStats(object):

    def __init__(self, file_path, size, progress_notify=None):
        self.file_path = file_path
        self.size = size
        self._last_check = 0
        self.received = 0
        #needed for speed calculation

        self._received_last = Tuple()
        self._speeds = Tuple()
        self._last_speeds = [Tuple(), Tuple()]

        self._progress_notify = progress_notify

    def _refresh_speed(self, status_check, seconds=1):
        return self._last_check + seconds < status_check

    def update_progress(self, status, refresh_rate=1):
        if self._refresh_speed(status.check, seconds=refresh_rate):
            self._update_progress(status)

    def _update_progress(self, status):
        received_now = Tuple(status.chunks_received)
        received_diff = received_now - self._received_last

        self._last_speeds[1] = self._last_speeds[0]
        self._last_speeds[0] = self._speeds

        self._speeds = received_diff/float(status.check - self._last_check)

        self._received_last = received_now

        self._last_check = status.check

        if self._progress_notify:
            self._progress_notify(self.percent)

    @property
    def speed(self):
        last = [sum(x) for x in self._last_speeds if x]
        return (self._speeds.sum() + sum(last)) / (1 + len(last))

    @property
    def percent(self):
        if not self.size:
            return 0

        return (self.received * 100) / self.size

    def is_completed(self):
        return self.received == self.size