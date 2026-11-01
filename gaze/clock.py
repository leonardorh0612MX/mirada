"""Monotonic millisecond clock for MediaPipe VIDEO mode. Stdlib only.

detect_for_video requires strictly increasing timestamps. Two frames
inside one millisecond collide, and two perf_counter bases on one
landmarker run backwards across phases (record_session crash
20261029-222025: env-check stamps on env_t0+500, then calibration
stamps restarting near zero). One MonoClock per landmarker fixes both:
collisions bump forward by 1 ms.
"""

import time


class MonoClock:
    def __init__(self, time_fn=time.perf_counter):
        self._time_fn = time_fn
        self._t0 = time_fn()
        self._last = 0

    def now_ms(self):
        ms = int((self._time_fn() - self._t0) * 1000)
        if ms <= self._last:
            ms = self._last + 1
        self._last = ms
        return ms
