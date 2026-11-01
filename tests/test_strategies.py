"""T14 harness: A/B/C/D comparison on a synthetic drifted session. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.replay import error_over_time as eot_a, replay_a, summarize
from eval.strategies import error_over_time, mean_error, run_strategy
from eval.synthetic import make_anchors, make_session


class TestStrategies(unittest.TestCase):
    def setUp(self):
        self.matrix, self.events, self.dots = make_session(duration_s=600.0, drift_px_s=0.05)

    def compare(self, anchors, **kw):
        # p0=1.0: weak prior suits dense synthetic anchors. Product default
        # p0=1e-3 is for sparse real anchors; tuning that trade is T14 work.
        kw = {"p0": 1.0, "lam": 0.95, **kw}
        preds, log = run_strategy(self.events, self.dots, self.matrix, anchors, **kw)
        return mean_error(error_over_time(preds, self.dots)), log

    def test_c_beats_a_on_drift(self):
        a = summarize(eot_a(replay_a(self.events, self.matrix), self.dots))["mean_px"]
        c, _ = self.compare(make_anchors(noise_px=8.0))
        self.assertLess(c, a / 2.0)

    def test_d_beats_c_with_tighter_anchors(self):
        c, _ = self.compare(make_anchors(noise_px=8.0))
        d, _ = self.compare(make_anchors(noise_px=2.0))
        self.assertLess(d, c)

    def test_b_sparse_clicks_help_less_than_c(self):
        c, _ = self.compare(make_anchors(noise_px=8.0))
        b, _ = self.compare(make_anchors(noise_px=0.0, every_s=120.0, conf=1.0))
        a = summarize(eot_a(replay_a(self.events, self.matrix), self.dots))["mean_px"]
        self.assertLess(b, a)
        self.assertLess(c, b)

    def test_bad_anchors_rejected(self):
        noisy = [(t, x + 500.0, y, cf, s) for t, x, y, cf, s in make_anchors(noise_px=8.0)]
        _, log = run_strategy(self.events, self.dots, self.matrix, noisy)
        accepted = [l for l in log if l[1]]
        self.assertEqual(len(accepted), 0)


if __name__ == "__main__":
    unittest.main()
