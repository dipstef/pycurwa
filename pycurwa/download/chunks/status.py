from collections import OrderedDict
import numbers
import operator

from collected.sequence import partition

from ..files import ChunksDict


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


class ChunksCompletion(object):

    def __init__(self, chunks=()):
        completed, remaining = partition(lambda chunk: chunk.is_completed(), chunks)

        self.size = sum(chunk.size for chunk in chunks) if chunks else 0
        self._chunks = ChunksDict(chunks)

        self.completed = ChunksDict(completed)
        self.failed = ChunksDict()

        self.remaining = remaining

    def update_progress(self, status):
        for chunk in self.completed.values():
            if chunk.id in status.failed:
                del self.completed[chunk.id]

        for chunk in self.failed.values():
            if chunk.id in status.completed:
                del self.failed[chunk.id]

        self.completed.update(ChunksDict(status.completed))
        self.failed.update(ChunksDict(status.failed))


    @property
    def chunks_received(self):
        return ChunkStatus(((chunk.id, chunk.received) for chunk in self.remaining))

    def is_completed(self):
        return all(chunk.is_completed() for chunk in self._chunks.values())

    def is_finished(self):
        return len(self.completed) >= len(self._chunks) or bool(self.failed)


class ChunksProgress(ChunksCompletion):

    def __init__(self, chunks, refresh_rate=1):
        super(ChunksProgress, self).__init__(chunks)
        self._last_check = 0

        self._last_received = ChunkStatus()
        self._last_speeds = ChunkStatus()

        self._last_two_speeds = ({}, {})
        self._speed_refresh_time = refresh_rate

    def update_progress(self, status):
        super(ChunksProgress, self).update_progress(status)
        if self._is_speed_refresh_time(status.check):
            self._update_progress(status.check)

    def _is_speed_refresh_time(self, status_time):
        return self._last_check + self._speed_refresh_time < status_time

    def _update_progress(self, status_time):
        received_now = self.chunks_received
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
    def percent(self):
        return (self._last_received.sum() * 100) / self.size


class DownloadStats(object):

    def __init__(self, path, size, speed):
        self.path = path
        self.size = size
        self.speed = speed

    def __str__(self):
        return '%s:, size: %d, speed: %d' % (self.path, self.size, self.speed)
