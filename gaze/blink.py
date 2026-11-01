"""Double-blink detection from eye landmarks. Pure, timestamp-driven.

EAR (eye aspect ratio) per eye = lid distance / eye width. A closure is
EAR below threshold. A deliberate double blink is two closures within
600 ms, after >= 200 ms of open eyes, with 800 ms debounce after firing.
Landmark indices (established MediaPipe topology): upper/lower lid
left 159/145, right 386/374, corners as in features.py.
"""

LEFT_LID, LEFT_LOW = 159, 145
RIGHT_LID, RIGHT_LOW = 386, 374


class LongBlink:
    """Single deliberate hold: eyes shut continuously >= hold_s.

    Natural blinks last ~100 ms. A 450 ms hold never collides with them.
    Chosen after Oct 27 data: doubles detected 5/5 but singles misfired 5/5
    because natural blinks pair up inside the trial window.
    """

    def __init__(self, ear_threshold=0.21, hold_s=0.45, debounce_s=0.8,
                 open_margin=1.25, grace_s=0.15):
        self.ear_threshold = ear_threshold
        self.open_threshold = ear_threshold * open_margin
        self.hold_s = hold_s
        self.debounce_s = debounce_s
        self.grace_s = grace_s
        self._closed_at = None
        self._fired_at = None
        self._opened_at = None
        self._invalid_at = None

    def holding(self):
        """A closure is in progress (for progress feedback)."""
        return self._closed_at is not None

    def hold_time(self, t):
        """Seconds since the current closure started, 0 when open."""
        return t - self._closed_at if self._closed_at is not None else 0.0

    def update(self, ear, t):
        """Feed one (ear, t_seconds). Returns 'select' on a confirmed hold.

        Missing frames (None) never count as closed. But a blink often
        breaks tracking mid-closure, so an active closure survives short
        invalid gaps (< 300 ms) instead of resetting; a hold interrupted
        by >= 300 ms of invalid frames is cancelled, and gap time never
        counts toward the hold (the closure start is rebased on return).
        Without this a stale hold fires on tracking return: a phantom
        press the user never made (board 20261029-135520). Schmitt
        trigger: closes below ear_threshold, opens only above
        open_threshold, so a marginal hold flickering near the line
        (beta 20261028: closed EAR 0.18 vs threshold 0.19) does not reset.
        """
        if self._fired_at is not None and t - self._fired_at < self.debounce_s:
            return None
        if ear is None:
            if self._closed_at is not None:
                if self._invalid_at is None:
                    self._invalid_at = t
                elif t - self._invalid_at >= 0.3:
                    self._closed_at = None
                    self._opened_at = None
                    self._invalid_at = None
            return None
        if self._invalid_at is not None:
            if self._closed_at is not None:
                self._closed_at += t - self._invalid_at
            self._invalid_at = None
        if self._closed_at is None:
            if ear < self.ear_threshold:
                self._closed_at = t
                self._opened_at = None
        elif ear > self.open_threshold:
            # Brief excursions are landmark flicker (low light), not opening:
            # reset only after a sustained opening beyond the grace period.
            if self._opened_at is None:
                self._opened_at = t
            elif t - self._opened_at > self.grace_s:
                self._closed_at = None
                self._opened_at = None
        else:
            self._opened_at = None
            if t - self._closed_at >= self.hold_s:
                self._fired_at = t
                self._closed_at = None
                return "select"
        return None


def eye_aspect_ratio(landmarks, corner_a, corner_b, lid, low):
    a, b, u, l = landmarks[corner_a], landmarks[corner_b], landmarks[lid], landmarks[low]
    width = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    if width < 1e-6:
        return None
    height = ((u[0] - l[0]) ** 2 + (u[1] - l[1]) ** 2) ** 0.5
    return height / width


def mean_ear(landmarks):
    from .features import LEFT_INNER, LEFT_OUTER, RIGHT_INNER, RIGHT_OUTER

    left = eye_aspect_ratio(landmarks, LEFT_OUTER, LEFT_INNER, LEFT_LID, LEFT_LOW)
    right = eye_aspect_ratio(landmarks, RIGHT_OUTER, RIGHT_INNER, RIGHT_LID, RIGHT_LOW)
    if left is None or right is None:
        return None
    return (left + right) / 2.0


class DoubleBlink:
    def __init__(self, ear_threshold=0.21, double_window_s=0.6,
                 min_open_s=0.2, min_closed_s=0.06, debounce_s=0.8):
        self.ear_threshold = ear_threshold
        self.double_window_s = double_window_s
        self.min_open_s = min_open_s
        self.min_closed_s = min_closed_s
        self.debounce_s = debounce_s
        self._state = "open"  # open -> closed1 -> open_gap -> closed2
        self._closed_at = None
        self._opened_at = None
        self._fired_at = None

    def update(self, ear, t):
        """Feed one (ear, t_seconds). Returns 'select' on a deliberate double."""
        if ear is None:
            return None
        if self._fired_at is not None and t - self._fired_at < self.debounce_s:
            return None
        closed = ear < self.ear_threshold
        if self._state == "open":
            if closed:
                self._state = "closed1"
                self._closed_at = t
        elif self._state == "closed1":
            if not closed:
                if t - self._closed_at >= self.min_closed_s:
                    self._state = "open_gap"
                    self._opened_at = t
                else:
                    self._state = "open"  # flicker, not a blink
        elif self._state == "open_gap":
            gap = t - self._opened_at
            if gap > self.double_window_s + self.min_open_s:
                self._state = "open"
            elif closed and gap >= self.min_open_s:
                self._state = "closed2"
                self._closed_at = t
        elif self._state == "closed2":
            if not closed:
                if t - self._closed_at >= self.min_closed_s:
                    self._fired_at = t
                    self._state = "open"
                    return "select"
                self._state = "open_gap"
                self._opened_at = t
        return None
