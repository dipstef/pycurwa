import numbers
import operator


class Tuple(tuple):

    def __new__(cls, seq=()):
        return super(Tuple, cls).__new__(cls, seq)

    def __add__(self, other):
        return self._zip_op(operator.add, other)

    def __sub__(self, other):
        return self._zip_op(operator.sub, other)

    def __mul__(self, other):
        return self._zip_tuple_or_number(operator.mul, other)

    def __div__(self, other):
        return self._zip_tuple_or_number(operator.div, other)

    def _zip_tuple_or_number(self, op, other):
        if isinstance(other, numbers.Number):
            other = (other, ) * len(self)
        return self._zip_op(op, other)

    def _zip_op(self, op, other):
        assert len(other) == len(self)

        return self.__class__(op(*zip_tuple) for zip_tuple in zip(self, other))

    def sum(self):
        return sum(self)


class DownloadStats(object):

    def __init__(self, file_path, size, chunks, progress_notify=None):
        self.file_path = file_path
        self.size = size
        self.chunks = chunks
        self._last_check = 0

        #needed for speed calculation
        zeros = (0, ) * len(chunks)
        self._received_last = Tuple(zeros)
        self._speeds = Tuple(zeros)
        self._last_speeds = [Tuple(zeros), Tuple(zeros)]

        self._progress_notify = progress_notify

    def _refresh_speed(self, now, seconds=1):
        return self._last_check + seconds < now

    def update_progress(self, now, refresh_rate=1):
        if self._refresh_speed(now, seconds=refresh_rate):
            self._update_progress(now)

    def _update_progress(self, now):
        received_now = Tuple(chunk.received for chunk in self.chunks)
        received_diff = received_now - self._received_last

        self._last_speeds[1] = self._last_speeds[0]
        self._last_speeds[0] = self._speeds

        self._speeds = received_diff/float(now - self._last_check)

        self._received_last = received_now

        self._last_check = now

        if self._progress_notify:
            self._progress_notify(self.percent)

    @property
    def speed(self):
        last = [sum(x) for x in self._last_speeds if x]
        return (self._speeds.sum() + sum(last)) / (1 + len(last))

    @property
    def received(self):
        return sum([chunk.received for chunk in self.chunks])

    @property
    def percent(self):
        if not self.size:
            return 0

        return (self.received * 100) / self.size

    def is_completed(self):
        return self.received == self.size