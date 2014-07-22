class DownloadStats(object):

    def __init__(self, file_path, size, chunks, progress_notify=None):
        self.file_path = file_path
        self.size = size
        self.chunks = chunks
        self._last_check = 0

        #needed for speed calculation
        self._last_arrived = []
        self._speeds = []
        self._last_speeds = [0, 0]

        self._progress_notify = progress_notify
        self.size = 0

    def refresh_speed(self, now, seconds=1):
        return self._last_check + seconds < now

    def update_progress(self, now):
        diff = [c.arrived - self._last_arrived_size(i) for i, c in enumerate(self.chunks)]

        self._last_speeds[1] = self._last_speeds[0]
        self._last_speeds[0] = self._speeds
        self._speeds = [float(a) / (now - self._last_check) for a in diff]
        self._last_arrived = [c.arrived for c in self.chunks]

        self._last_check = now

        if self._progress_notify:
            self._progress_notify(self.percent)

    def _last_arrived_size(self, i):
        return self._last_arrived[i] if len(self._last_arrived) > i else 0

    @property
    def speed(self):
        last = [sum(x) for x in self._last_speeds if x]
        return (sum(self._speeds) + sum(last)) / (1 + len(last))

    @property
    def arrived(self):
        return sum([c.arrived for c in self.chunks])

    @property
    def percent(self):
        if not self.size:
            return 0
        return (self.arrived * 100) / self.size

    def is_completed(self):
        return self.arrived == self.size