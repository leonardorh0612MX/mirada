"""JumpGate: saccades confirmed, spikes dropped, shut eyes frozen."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.saccade import JumpGate


class TestJumpGate(unittest.TestCase):
    def test_small_steps_ok(self):
        g = JumpGate()
        for i in range(10):
            self.assertEqual(g.check(100 + i * 10, 100, None, 100, 100), "ok")

    def test_single_spike_dropped_then_ok(self):
        g = JumpGate()
        self.assertEqual(g.check(900, 100, None, 100, 100), "drop")
        self.assertEqual(g.check(105, 100, None, 100, 100), "ok")

    def test_three_agreeing_jumps_snap(self):
        g = JumpGate()
        self.assertEqual(g.check(900, 100, "f1", 100, 100), "drop")
        self.assertEqual(g.check(910, 105, "f2", 100, 100), "drop")
        self.assertEqual(g.check(905, 95, "f3", 100, 100), "snap")
        self.assertEqual(g.frames, ["f1", "f2", "f3"])
        self.assertEqual(len(g.points), 3)

    def test_scattered_jumps_never_snap(self):
        g = JumpGate()
        self.assertEqual(g.check(900, 100, None, 100, 100), "drop")
        self.assertEqual(g.check(100, 900, None, 100, 100), "drop")
        self.assertEqual(g.check(900, 900, None, 100, 100), "drop")
        self.assertEqual(g.check(100, 900, None, 100, 100), "drop")

    def test_wide_agree_confirms_noisy_saccade(self):
        # 220px scatter between confirming frames: resets at 150, snaps
        # at the board's 250 (board-180002 jumps never confirmed).
        narrow = JumpGate()
        wide = JumpGate(agree_px=250.0)
        frames = [(900, 100), (900, 320), (900, 200)]
        narrow_out = [narrow.check(x, y, None, 100, 100) for x, y in frames]
        wide_out = [wide.check(x, y, None, 100, 100) for x, y in frames]
        self.assertNotIn("snap", narrow_out)
        self.assertEqual(wide_out[-1], "snap")

    def test_snap_suppressed_while_shut(self):
        g = JumpGate()
        for _ in range(5):
            self.assertEqual(
                g.check(900, 100, None, 100, 100, eyes_open=False), "drop")


if __name__ == "__main__":
    unittest.main()
