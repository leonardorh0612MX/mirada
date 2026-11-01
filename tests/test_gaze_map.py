"""T25: bilinear gaze map + bias-only consensus corrector. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corrector.corrector import BiasCorrector
from gaze.calibration import fit_calibration, fit_gaze_map
from gaze.features import expand_features, map_to_screen


def true_screen(f):
    """Ground truth with head-gaze interaction (world = Rh * ve)."""
    ex = (f[0] + f[2]) / 2.0
    ey = (f[1] + f[3]) / 2.0
    hx, hy, _ = f[4], f[5], f[6]
    x = 2900 + 4000 * ex + 300 * hx + 6000 * ex * hx
    y = 500 + 3500 * ey + 250 * hy + 5000 * ey * hy
    return (x, y)


def factorial_samples():
    out = []
    for gx in (-0.06, 0.0, 0.06):
        for gy in (-0.04, 0.0, 0.04):
            for hx in (-0.08, 0.0, 0.08):
                for hy in (-0.05, 0.05):
                    f = [gx, gy, gx * 0.9, gy * 0.9, hx, hy, 0.2]
                    out.append((f, *true_screen(f)))
    return out


class TestExpand(unittest.TestCase):
    def test_shape(self):
        z = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        self.assertEqual(len(expand_features(z)), 15)
        self.assertEqual(expand_features(z)[:7], z)


class TestGazeMap(unittest.TestCase):
    def test_held_out_posture_beats_linear(self):
        samples = factorial_samples()
        gm = fit_gaze_map(samples)
        lin = fit_calibration(samples)
        # Held-out posture hx=0.05, hy=-0.03 (never in training grid).
        errs_gm, errs_lin = [], []
        for gx in (-0.05, 0.03):
            for gy in (-0.03, 0.02):
                f = [gx, gy, gx * 0.9, gy * 0.9, 0.05, -0.03, 0.2]
                xt, yt = true_screen(f)
                xg, yg = gm.predict(f)
                xl, yl = map_to_screen(f, lin)
                errs_gm.append(((xg - xt) ** 2 + (yg - yt) ** 2) ** 0.5)
                errs_lin.append(((xl - xt) ** 2 + (yl - yt) ** 2) ** 0.5)
        self.assertLess(sum(errs_gm) / len(errs_gm),
                        0.75 * (sum(errs_lin) / len(errs_lin)))


MEANS = [0.0] * 7


def base(_f):
    return (1000.0, 500.0)


FEATS = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2]


class TestBiasCorrector(unittest.TestCase):
    def test_consensus_required(self):
        bc = BiasCorrector(base, MEANS)
        st1, _ = bc.update(FEATS, (1100.0, 500.0))
        st2, _ = bc.update(FEATS, (1100.0, 500.0))
        self.assertEqual((st1, st2), ("waiting", "waiting"))
        st3, info = bc.update(FEATS, (1100.0, 500.0))
        self.assertEqual(st3, "applied")
        self.assertLessEqual(info["shift"], 25.0)

    def test_single_poison_moves_nothing(self):
        bc = BiasCorrector(base, MEANS)
        for _ in range(2):
            bc.update(FEATS, (1100.0, 500.0))
        before = bc.predict(FEATS)
        bc.update(FEATS, (200.0, 900.0))  # disagreeing, no consensus
        self.assertEqual(bc.predict(FEATS), before)

    def test_trust_region_caps_shift(self):
        bc = BiasCorrector(base, MEANS)
        for _ in range(3):
            _, info = bc.update(FEATS, (1400.0, 500.0))
        self.assertLessEqual(info["shift"], 25.0)
        x, _ = bc.predict(FEATS)
        self.assertLessEqual(x - 1000.0, 25.0)

    def test_drift_converges_slowly(self):
        bc = BiasCorrector(base, MEANS)
        for _ in range(60):
            bc.update(FEATS, (1100.0, 500.0))  # true drift +100px
        x, _ = bc.predict(FEATS)
        self.assertGreater(x - 1000.0, 50.0)


if __name__ == "__main__":
    unittest.main()
