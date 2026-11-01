"""Saccade confirmation gate. Pure, no I/O.

A median window plus a hard jump-guard permanently rejects real
saccades: jumped frames are dropped, so the window never accumulates
the new location (board 20261029-171805: fast looks never move the
highlight, slow sweeps do). A real saccade parks at the new location
while noise snaps back, so: the first frame > jump_px from smooth
opens a candidacy; if confirm_n consecutive frames land within
agree_px of the candidate, the jump is accepted. Single spikes are
still dropped exactly as before.

Snaps are suppressed while the eyes are shut: eyes-closed landmarks
are near-constant garbage that would agree with itself and snap the
gaze point to fiction. While shut, gaze is unknowable; freezing is
correct.
"""


class JumpGate:
    def __init__(self, jump_px=400.0, agree_px=150.0, confirm_n=3):
        self.jump_px = jump_px
        self.agree_px = agree_px
        self.confirm_n = confirm_n
        self.cand = []  # [(x, y, feats)] consecutive agreeing jumps

    def reset(self):
        self.cand = []

    @property
    def points(self):
        return [(x, y) for x, y, _ in self.cand]

    @property
    def frames(self):
        return [f for _, _, f in self.cand]

    def check(self, px, py, feats, sx, sy, eyes_open=True):
        """Classify one prediction against smooth (sx, sy).

        Returns 'ok' (integrate), 'drop' (discard the frame) or 'snap'
        (jump confirmed: caller moves smooth to the candidate mean and
        primes its window from .frames, then calls reset()).
        """
        if ((px - sx) ** 2 + (py - sy) ** 2) ** 0.5 <= self.jump_px:
            self.cand = []
            return "ok"
        if not eyes_open:
            self.cand = []
            return "drop"
        if self.cand:
            mx = sum(x for x, _, _ in self.cand) / len(self.cand)
            my = sum(y for _, y, _ in self.cand) / len(self.cand)
            if ((px - mx) ** 2 + (py - my) ** 2) ** 0.5 > self.agree_px:
                self.cand = []  # scattered: start a new candidacy
        self.cand.append((px, py, feats))
        if len(self.cand) >= self.confirm_n:
            return "snap"
        return "drop"
