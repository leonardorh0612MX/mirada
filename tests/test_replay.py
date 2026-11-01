"""T8: replay A on a synthetic session with known drift. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.replay import drift_slope, error_over_time, replay_a, summarize
from eval.synthetic import make_session


class TestReplayA(unittest.TestCase):
    def test_recovers_injected_drift(self):
        matrix, events, dots = make_session(duration_s=600.0, drift_px_s=0.05)
        preds = replay_a(events, matrix)
        self.assertTrue(len(preds) > 100)
        series = error_over_time(preds, dots)
        self.assertEqual(len(series), 4)  # dots at 120, 240, 360, 480
        slope, _ = drift_slope(series)
        self.assertAlmostEqual(slope, 0.05, places=3)

    def test_summarize(self):
        matrix, events, dots = make_session(duration_s=300.0, drift_px_s=0.05)
        s = summarize(error_over_time(replay_a(events, matrix), dots))
        self.assertEqual(s["n"], 2)
        self.assertGreater(s["mean_px"], 0.0)
        self.assertAlmostEqual(s["slope_px_s"], 0.05, places=3)

    def test_no_dots(self):
        s = summarize(error_over_time([(1.0, (0.0, 0.0))], []))
        self.assertEqual(s["n"], 0)

    def test_zero_drift_flat(self):
        matrix, events, dots = make_session(duration_s=300.0, drift_px_s=0.0)
        series = error_over_time(replay_a(events, matrix), dots)
        slope, _ = drift_slope(series)
        self.assertAlmostEqual(slope, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
