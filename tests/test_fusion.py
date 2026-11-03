"""Fusion guards: cooldown repeats, posture freeze. Stdlib only."""
import unittest

from corrector.fusion import (PostureGuard, SelectionCooldown,
                              enrollment_spread)


class TestSelectionCooldown(unittest.TestCase):
    def test_repeat_rests_other_cells_teach(self):
        cd = SelectionCooldown(2.5)
        self.assertTrue(cd.allow("WATER", 100.0))
        self.assertFalse(cd.allow("WATER", 101.0))  # volunteer's 3-in-8s
        self.assertFalse(cd.allow("WATER", 102.4))
        self.assertTrue(cd.allow("YES", 102.0))  # other cells unaffected
        self.assertTrue(cd.allow("WATER", 102.6))  # window passed

    def test_denied_fire_does_not_extend_window(self):
        cd = SelectionCooldown(2.5)
        cd.allow("WATER", 100.0)
        cd.allow("WATER", 101.0)
        self.assertTrue(cd.allow("WATER", 102.6))


class TestPostureGuard(unittest.TestCase):
    def test_sustained_drift_freezes_transients_pass(self):
        g = PostureGuard(spread=0.05, factor=3.0, sustain_s=3.0)
        self.assertFalse(g.update(0.20, 0.0))  # over limit, not sustained
        self.assertFalse(g.update(0.20, 2.0))
        self.assertTrue(g.update(0.20, 3.1))  # sustained: frozen
        self.assertTrue(g.update(0.10, 4.0))  # middle band: stays frozen

    def test_return_recovers(self):
        g = PostureGuard(spread=0.05, factor=3.0, sustain_s=1.0)
        g.update(0.20, 0.0)
        g.update(0.20, 1.5)
        self.assertTrue(g.drifted)
        self.assertFalse(g.update(0.05, 2.0))  # back inside: learning

    def test_enrollment_spread_is_max_distance(self):
        means = [0.0, 0.0]
        samples = [([0.03, 0.04], 0, 0), ([0.0, 0.0], 1, 1)]
        self.assertAlmostEqual(enrollment_spread(samples, means), 0.05)
        self.assertGreater(enrollment_spread([], means), 0.0)


if __name__ == "__main__":
    unittest.main()
