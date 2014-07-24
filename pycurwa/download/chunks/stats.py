from collections import OrderedDict
import numbers
import operator


class ChunkStatus(OrderedDict):

    def __add__(self, other):
        return self._dict_operation(operator.add, other)

    def __sub__(self, other):
        return self._dict_operation(operator.sub, other)

    def __mul__(self, other):
        return self._dict_or_number_op(operator.mul, other)

    def __div__(self, other):
        return self._dict_or_number_op(operator.div, other)

    def _dict_or_number_op(self, op, other):
        if isinstance(other, numbers.Number):
            other = OrderedDict.fromkeys(self.keys(), value=other)
        return self._dict_operation(op, other)

    def _dict_operation(self, op, other):
        result = ChunkStatus(self)

        for chunk_id, other_value in other.iteritems():
            chunk_value = result.get(chunk_id)
            if chunk_value is not None:
                result[chunk_id] = op(chunk_value, other_value)

        return result

    def sum(self):
        return sum(self.values())


class DownloadStats(object):

    def __init__(self, file_path, size):
        self.file_path = file_path
        self.size = size
        self._last_check = 0

        #needed for speed calculation
        self.chunks_received = ChunkStatus()
        self.chunks_speeds = ChunkStatus()
        self._last_speeds = (self.chunks_speeds, ChunkStatus())

    def _refresh_speed(self, status_check, seconds=1):
        return self._last_check + seconds < status_check

    def update_progress(self, status, refresh_rate=1):
        if self._refresh_speed(status.check, seconds=refresh_rate):
            self._update_progress(status)

    def _update_progress(self, status):
        #received_now = Tuple(status.chunks_received)
        received_now = ChunkStatus(status.chunks_received)
        received_diff = received_now - self.chunks_received

        self._last_speeds = (self.chunks_speeds, self._last_speeds[0])

        self.chunks_speeds = received_diff/float(status.check - self._last_check)

        self.chunks_received = received_now

        self._last_check = status.check

    @property
    def speed(self):
        last = [sum(x.values()) for x in self._last_speeds if x]
        #print 'Last', last
        return (self.chunks_speeds.sum() + sum(last)) / (1 + len(last))

    @property
    def received(self):
        return sum(self.chunks_received.values())

    @property
    def percent(self):
        if not self.size:
            return 0

        return (self.received * 100) / self.size

    def is_completed(self):
        return self.received == self.size