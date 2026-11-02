"""T9: RLS convergence, adaptation, and the three gates. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corrector.corrector import BiasCorrector, Corrector
from corrector.rls import RLSFilter

M0 = [[400.0, 50.0, 400.0, -50.0, 960.0], [30.0, 300.0, -30.0, 300.0, 540.0]]


def feats(i, j):
    return [0.01 * i, 0.005 * j, -0.008 * i, 0.004 * (i - j)]


class TestRLS(unittest.TestCase):
    def test_converges_from_zero(self):
        # Large p0 = weak prior. Small p0 would bias toward w_init;
        # that bias is intended behavior, tested implicitly by test_follows_mapping_jump.
        f = RLSFilter(3, lam=1.0, p0=100.0)
        target = [2.0, -1.0, 0.5]
        import random
        rnd = random.Random(7)
        for _ in range(300):
            x = [rnd.uniform(-1, 1), rnd.uniform(-1, 1), 1.0]
            f.update(x, sum(a * b for a, b in zip(target, x)))
        self.assertAlmostEqual(f.predict([0.5, 0.25, 1.0]), 2 * 0.5 - 0.25 + 0.5, places=2)

    def test_bad_params_rejected(self):
        with self.assertRaises(ValueError):
            RLSFilter(3, lam=0.0)
        with self.assertRaises(ValueError):
            RLSFilter(3, w_init=[1.0])

    def test_weight_downscales_step(self):
        full = RLSFilter(2, lam=0.98, p0=1.0)
        part = RLSFilter(2, lam=0.98, p0=1.0)
        full.update([1.0, 1.0], 10.0)
        part.update([1.0, 1.0], 10.0, weight=0.25)
        self.assertLess(abs(part.predict([1.0, 1.0])),
                        abs(full.predict([1.0, 1.0])))
        self.assertGreater(part.predict([1.0, 1.0]), 0.0)


class TestGates(unittest.TestCase):
    def test_low_confidence_rejected(self):
        c = Corrector(M0)
        ok, reason = c.update(feats(1, 2), (960.0, 540.0), 0.1, 0.0)
        self.assertFalse(ok)
        self.assertEqual(reason, "low_confidence")

    def test_stale_rejected(self):
        c = Corrector(M0)
        ok, reason = c.update(feats(1, 2), (960.0, 540.0), 0.9, 30.0)
        self.assertFalse(ok)
        self.assertEqual(reason, "stale")

    def test_large_residual_quarantined(self):
        c = Corrector(M0, max_residual_px=10.0)
        before = c.predict(feats(1, 1))
        ok, reason = c.update(feats(1, 1), (10.0, 10.0), 0.99, 0.0)
        self.assertFalse(ok)
        self.assertEqual(reason, "large_residual")
        after = c.predict(feats(1, 1))
        self.assertEqual(before, after)  # filters untouched

    def test_good_anchor_applied(self):
        c = Corrector(M0)
        pred = c.predict(feats(3, 4))
        ok, reason = c.update(feats(3, 4), pred, 0.9, 0.0)
        self.assertTrue(ok)
        self.assertEqual(reason, "applied")


class TestAdaptation(unittest.TestCase):
    def test_follows_mapping_jump(self):
        c = Corrector(M0, lam=0.9, p0=1.0)
        jumped = [[m + 100.0 for m in row[:4]] + [row[4] + 200.0] for row in M0]

        def target(m, f):
            v = f + [1.0]
            return (sum(m[0][j] * v[j] for j in range(5)),
                    sum(m[1][j] * v[j] for j in range(5)))

        err_before = abs(c.predict(feats(5, 5))[0] - target(jumped, feats(5, 5))[0])
        for i in range(60):
            f = feats(i % 9, (i * 2) % 7)
            t = target(jumped, f)
            c.min_confidence = 0.0
            c.max_residual_px = 1e9
            c.update(f, t, 1.0, 0.0)
        err_after = abs(c.predict(feats(5, 5))[0] - target(jumped, feats(5, 5))[0])
        self.assertLess(err_after, err_before / 5.0)


class TestBiasCertain(unittest.TestCase):
    def make(self):
        return BiasCorrector(lambda f: (100.0, 100.0), [0.0] * 7)

    def test_certain_applies_first_try(self):
        c = self.make()
        stt, info = c.update([0.0] * 7, (400.0, 100.0), certain=True)
        self.assertEqual(stt, "applied")
        self.assertTrue(info["certain"])

    def test_certain_moves_toward_anchor(self):
        c = self.make()
        before = c.predict([0.0] * 7)
        c.update([0.0] * 7, (400.0, 100.0), certain=True)
        after = c.predict([0.0] * 7)
        self.assertLess(abs(after[0] - 400.0), abs(before[0] - 400.0))

    def test_certain_bounded_by_trust_region(self):
        c = self.make()
        _, info = c.update([0.0] * 7, (5000.0, 100.0), certain=True)
        self.assertLessEqual(info["shift"], 25.0)

    def test_bias_only_freezes_slope(self):
        # web-20261101-210049 regression: full slope updates re-tilted
        # the plane per selection and neighbours warped progressively.
        c = BiasCorrector(lambda f: (100.0, 100.0), [0.0] * 7,
                          certain_bias_only=True, trust_px=15.0)
        feats = [0.0] * 7
        feats[4], feats[5] = 0.08, -0.05  # off-centre head at selection
        for anch in [(400.0, 100.0), (100.0, 400.0), (300.0, 300.0)]:
            stt, info = c.update(feats, anch, certain=True)
            self.assertEqual(stt, "applied")
            self.assertLessEqual(info["shift"], 15.0)
        self.assertEqual(c.ax.w[1], 0.0)
        self.assertEqual(c.ay.w[1], 0.0)

    def test_bias_only_flags_warp_residual(self):
        c = BiasCorrector(lambda f: (100.0, 100.0), [0.0] * 7,
                          certain_bias_only=True)
        stt, _ = c.update([0.0] * 7, (5000.0, 100.0), certain=True)
        self.assertEqual(stt, "flagged")
        self.assertEqual(c.predict([0.0] * 7), (100.0, 100.0))

    def test_uncertain_waits_without_consensus(self):
        # Scattered biases across targets: the regional-error case that
        # left board 20261029-163748 with zero applied anchors.
        c = self.make()
        stt, _ = c.update([0.0] * 7, (400.0, 100.0))
        self.assertEqual(stt, "waiting")
        for ax, ay in [(100.0, 400.0), (400.0, 400.0), (100.0, 100.0)]:
            stt, _ = c.update([0.0] * 7, (ax, ay))
        self.assertEqual(stt, "waiting")


if __name__ == "__main__":
    unittest.main()
