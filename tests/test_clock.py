"""MonoClock: strictly increasing even when time stands still."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.clock import MonoClock


class TestMonoClock(unittest.TestCase):
    def test_frozen_time_still_increases(self):
        c = MonoClock(time_fn=lambda: 100.0)
        stamps = [c.now_ms() for _ in range(5)]
        self.assertEqual(stamps, [1, 2, 3, 4, 5])

    def test_advancing_time_passes_through(self):
        t = [0.0]
        c = MonoClock(time_fn=lambda: t[0])
        t[0] = 0.010
        self.assertEqual(c.now_ms(), 10)
        t[0] = 0.025
        self.assertEqual(c.now_ms(), 25)

    def test_backwards_time_bumps_forward(self):
        t = [1.0]
        c = MonoClock(time_fn=lambda: t[0])
        t[0] = 1.05
        self.assertEqual(c.now_ms(), 50)
        t[0] = 0.5  # clock base changed under us: never go back
        self.assertEqual(c.now_ms(), 51)


if __name__ == "__main__":
    unittest.main()
