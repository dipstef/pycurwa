from collections import OrderedDict
import numbers
import operator
import os


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

    def __init__(self, file_path, size):
        self.file_path = file_path
        self.size = size
        self._last_check = 0

        #needed for speed calculation
        self.chunks_received = ChunkStatus()

        self.chunk_speeds = ChunkStatus()
        self.last_speeds = ChunkStatus()

        self._last_speeds = ({}, {})
        self.lasts_speeds = []
        self.speeds = []
        self.updates = 0

        self.lastsReceived = []
        self.lastArrived = []
        self.lastSpeeds = ((), ())
        #self._last_speeds = (self.chunks_speeds, ChunkStatus())
        self.Speeds = []

    def _refresh_speed(self, status_check, seconds=1):
        return self._last_check + seconds < status_check

    def update_progress(self, status, refresh_rate=1):
        if self._refresh_speed(status.check, seconds=refresh_rate):
            self._update_progress(status)

    def _update_progress(self, status):
        self.updates += 1

        received_now = ChunkStatus(status.chunks_received)
        received_diff = received_now - self.chunks_received

        last_speeds = received_diff/float(status.check - self._last_check)

        self._update_speed_old(status.check, status.chunks_received)
        self._update_speed(last_speeds)

        self.chunks_received = received_now

        self._last_check = status.check

        self.lasts_speeds.append(self.last_speeds)

    def _update_speed(self, last_speeds):
        self.speeds.append(last_speeds)

        if self.chunk_speeds:
            self.chunk_speeds = (last_speeds + self.chunk_speeds) / float(2)
        else:
            self.chunk_speeds = last_speeds

        self._last_speeds = (self.last_speeds, self._last_speeds[0])

        last = [sum(x.values()) for x in self._last_speeds if x]

        last_active = [x for x in self._last_speeds if x]
        current_speeds = last_speeds
        for last_active_speed in last_active:
            current_speeds += last_active_speed
        current_speeds /= 1 + len(last)

        speed_old2 = current_speeds.sum()

        speed_old = (last_speeds.sum() + sum(last)) / (1 + len(last))

        speed = sum([sum(speed.values()) for speed in self.speeds])/len(self.speeds)

        print
        print 'Speed:', speed
        print 'Self speed: ', self.speed
        print 'Speed Old:', speed_old
        print 'Speed Ald:', speed_old2
        print 'Speed Uld:', self.speed_old

        self.last_speeds = last_speeds

    def _update_speed_old(self, now, received):
        last_received = OrderedDict()

        last_received_len = len(self.lastsReceived)

        for chunk_id, arrived in enumerate(received.values()):
            if last_received_len > chunk_id:
                last_received[chunk_id] = self.lastsReceived[chunk_id]
            else:
                last_received[chunk_id] = 0

        last_received = last_received.values()

        diff = [arrived - last_received[chunk_id] for chunk_id, arrived in enumerate(received.values())]

        self.lastSpeeds = (self.Speeds, self.lastSpeeds[0])

        self.Speeds = [float(a) / (now - self._last_check) for a in diff]

        self.lastsReceived = received.values()


    #current speed
    @property
    def speed(self):
        return self.chunk_speeds.sum()

    @property
    def speed_old(self):
        last = [sum(x) for x in self.lastSpeeds if x]

        return (sum(self.Speeds) + sum(last)) / (1 + len(last))


    @property
    def received(self):
        return sum(self.chunks_received.values())

    @property
    def percent(self):
        if not self.size:
            return 0

        return (self.received * 100) / self.size

    def is_completed(self):
        file_size = os.path.getsize(self.file_path)
        return file_size == self.size
