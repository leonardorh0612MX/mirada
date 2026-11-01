"""T23: double-blink state machine on synthetic EAR streams. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.blink import DoubleBlink, LongBlink

OPEN, SHUT = 0.30, 0.10


def feed(seq, dt=0.05):
    det = DoubleBlink()
    hits = []
    for i, ear in enumerate(seq):
        if det.update(ear, i * dt) == "select":
            hits.append(i * dt)
    return hits


def blink_block(open_before, shut_frames, open_after):
    return [OPEN] * open_before + [SHUT] * shut_frames + [OPEN] * open_after


class TestDoubleBlink(unittest.TestCase):
    def test_deliberate_double_fires(self):
        seq = blink_block(10, 3, 6) + [SHUT] * 3 + [OPEN] * 10
        hits = feed(seq)
        self.assertEqual(len(hits), 1)

    def test_single_natural_blink_never_fires(self):
        seq = blink_block(10, 4, 40)
        self.assertEqual(feed(seq), [])

    def test_two_slow_blinks_do_not_fire(self):
        # Second closure 1.5 s after the first: outside the 600 ms window.
        seq = blink_block(10, 3, 30) + [SHUT] * 3 + [OPEN] * 10
        self.assertEqual(feed(seq), [])

    def test_debounce_blocks_triple(self):
        seq = (blink_block(10, 3, 6) + [SHUT] * 3 + [OPEN] * 2
               + [SHUT] * 3 + [OPEN] * 10)
        hits = feed(seq)
        self.assertEqual(len(hits), 1)

    def test_none_ignored(self):
        det = DoubleBlink()
        self.assertIsNone(det.update(None, 0.0))


class TestLongBlink(unittest.TestCase):
    def feed(self, seq, dt=0.05):
        det = LongBlink()
        hits = []
        for i, ear in enumerate(seq):
            if det.update(ear, i * dt) == "select":
                hits.append(i * dt)
        return hits

    def test_hold_fires(self):
        self.assertEqual(len(self.feed([OPEN] * 10 + [SHUT] * 12 + [OPEN] * 10)), 1)

    def test_natural_blink_never_fires(self):
        self.assertEqual(self.feed([OPEN] * 10 + [SHUT] * 2 + [OPEN] * 40), [])

    def test_blink_burst_never_fires(self):
        seq = [OPEN] * 10 + [SHUT] * 2 + [OPEN] * 4 + [SHUT] * 2 + [OPEN] * 40
        self.assertEqual(self.feed(seq), [])

    def test_none_never_counts_as_closed(self):
        self.assertEqual(self.feed([None] * 40), [])

    def test_hold_survives_short_tracking_gap(self):
        seq = [OPEN] * 5 + [SHUT] * 6 + [None] * 3 + [SHUT] * 6 + [OPEN] * 10
        self.assertEqual(len(self.feed(seq)), 1)

    def test_stale_hold_cancelled_after_long_tracking_gap(self):
        # 6 shut + 8 invalid (0.35 s blind) + 6 shut: the pre-gap closure
        # is stale, the post-gap run is too short. No phantom select.
        seq = [OPEN] * 5 + [SHUT] * 6 + [None] * 8 + [SHUT] * 6 + [OPEN] * 10
        self.assertEqual(self.feed(seq), [])

    def test_gap_time_does_not_count_toward_hold(self):
        # 0.15 s shut + 0.25 s gap + 0.25 s shut spans 0.65 s but only
        # 0.40 s is known shut < 0.45 s hold: must not fire.
        seq = [OPEN] * 5 + [SHUT] * 3 + [None] * 5 + [SHUT] * 5 + [OPEN] * 10
        self.assertEqual(self.feed(seq), [])

    def test_brief_opening_inside_grace_survives(self):
        det = LongBlink(ear_threshold=0.19, hold_s=0.45, grace_s=0.15)
        seq = [0.30] * 3 + [0.10] * 4 + [0.35] * 2 + [0.10] * 8
        hits = sum(det.update(v, i * 0.05) == "select"
                   for i, v in enumerate(seq))
        self.assertEqual(hits, 1)

    def test_sustained_opening_resets(self):
        det = LongBlink(ear_threshold=0.19, hold_s=0.45, grace_s=0.15)
        seq = [0.10] * 4 + [0.35] * 8 + [0.10] * 12
        hits = sum(det.update(v, i * 0.05) == "select"
                   for i, v in enumerate(seq))
        self.assertEqual(hits, 1)

    def test_holding_flag_tracks_closure(self):
        det = LongBlink(ear_threshold=0.19, hold_s=10.0)
        self.assertFalse(det.holding())
        det.update(0.10, 1.0)
        self.assertTrue(det.holding())
        self.assertAlmostEqual(det.hold_time(1.3), 0.3)

    def test_marginal_hold_survives_flicker(self):
        # Closed EAR hovering just above the close line must not reset.
        det = LongBlink(ear_threshold=0.19, hold_s=0.45)
        mid = 0.19 * 1.1  # above close, below open (x1.25)
        hits = sum(det.update(v, i * 0.05) == "select"
                   for i, v in enumerate([0.30] * 5 + [0.10] * 3 + [mid] * 9))
        self.assertEqual(hits, 1)


if __name__ == "__main__":
    unittest.main()
