from collections import OrderedDict
import numbers
import operator
from pycurwa.download.files import ChunksDict
from pycurwa.requests import RequestsStatus


class ChunkStatus(OrderedDict):

    def __add__(self, other):
        return self._dict_operation(operator.add, other)

    def __sub__(self, other):
        return self._dict_operation(operator.sub, other)

    def __mul__(self, other):
        return self._number_operation(operator.mul, other)

    def __div__(self, other):
        return self._number_operation(operator.div, other)

    def _number_operation(self, op, other):
        assert isinstance(other, numbers.Number)

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

    def __init__(self, size, refresh_rate=1):
        self.size = size

        self._last_check = 0

        self._last_received = ChunkStatus()

        self._last_speeds = ChunkStatus()

        self._last_two_speeds = ({}, {})
        self._speed_refresh_time = refresh_rate

    def update_progress(self, status):
        if self._is_speed_refresh_time(status.check):
            self._update_progress(status.check, status.received)

    def _is_speed_refresh_time(self, status_time):
        return self._last_check + self._speed_refresh_time < status_time

    def _update_progress(self, status_time, received_now):
        received_diff = received_now - self._last_received

        last_speeds = received_diff/float(status_time - self._last_check)

        self._last_two_speeds = (self._last_speeds, self._last_two_speeds[0])
        self._last_received = received_now
        self._last_speeds = last_speeds
        self._last_check = status_time

    #current speed
    @property
    def speed(self):
        return sum(self.chunks_speeds.values())

    @property
    def chunks_speeds(self):
        last = [x for x in self._last_two_speeds if x]
        current_speeds = reduce(operator.add, last, self._last_speeds) / (1 + len(last))
        return current_speeds


    @property
    def received(self):
        return self._last_received.sum()

    @property
    def percent(self):
        return (self.received * 100) / self.size


class HttpChunksStatus(RequestsStatus):

    def __init__(self, status, received):
        super(HttpChunksStatus, self).__init__(ChunksDict(status.completed), ChunksDict(status.failed), status.check)
        self.received = ChunkStatus(received)