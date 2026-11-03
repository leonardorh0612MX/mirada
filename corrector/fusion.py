"""Fusion: coarse selection labels + geometric guardrail. Stdlib only.

Two lessons from the first volunteer session (web-20261102-171626):
a stuck highlight fired WATER 3x in 8 s and each "certain" anchor
deformed the map until the board died; and nothing noticed the posture
had left the enrollment regime. So selections carry tile-size
uncertainty (see BiasCorrector sigma_px), repeats cool down, and a
posture guard freezes learning outside the calibrated regime instead
of learning there. Pure (tested).
"""
import math


def enrollment_spread(samples, means):
    """Max feature-space distance from the enrollment mean. Pure.

    samples: [(feats, x, y)]. The guard's ruler: live drift is measured
    in multiples of how much the enrollment itself moved.
    """
    if not samples:
        return 0.05
    return max(math.dist(s[0], means) for s in samples)


class SelectionCooldown:
    """Same-cell gaze repeats rest before they may teach again. Pure.

    Speech still fires every hold (visible, reversible); only the
    anchor that would deform the map waits out the cooldown.
    """

    def __init__(self, cooldown_s=2.5):
        self.cooldown_s = cooldown_s
        self._last = {}  # key -> time of last anchor-bearing fire

    def allow(self, key, now):
        """True once per cooldown window; records allowed fires."""
        if now - self._last.get(key, float("-inf")) < self.cooldown_s:
            return False
        self._last[key] = now
        return True


class PostureGuard:
    """Freeze learning when posture leaves the enrollment regime. Pure.

    dist is the live feature-space distance from the enrollment mean.
    Drifted after sustain_s beyond factor * spread; recovers below
    half that line (hysteresis so the prompt doesn't flicker).
    """

    def __init__(self, spread, factor=3.0, sustain_s=3.0):
        self.limit = max(spread, 1e-6) * factor
        self.sustain_s = sustain_s
        self._since = None
        self._drifted = False

    @property
    def drifted(self):
        return self._drifted

    def update(self, dist, now):
        """Feed one distance sample. Returns drifted state."""
        if dist > self.limit:
            if self._since is None:
                self._since = now
            if now - self._since >= self.sustain_s:
                self._drifted = True
        elif dist < self.limit * 0.5:
            self._since = None
            self._drifted = False
        else:
            self._since = None
        return self._drifted
