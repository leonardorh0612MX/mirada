"""T6: calibration fit and dot protocol. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.calibration import (
    calibration_points,
    dot_error,
    dot_schedule,
    fit_calibration,
)
from gaze.features import map_to_screen


TRUE_M = [[400.0, 50.0, 400.0, -50.0, 960.0], [30.0, 300.0, -30.0, 300.0, 540.0]]


def synth_features(i):
    # Deliberately non-collinear: a calibration stare sequence must cover
    # diverse gaze positions or the fit is singular (caught by this test).
    return [0.01 * i, -0.02 * (i % 5) + 0.003 * i, 0.015 * ((i * 3) % 7), 0.005 * i - 0.01 * (i % 3)]


_REAL_M = [[1200.0, 300.0, 1200.0, -300.0, 0.0, 900.0, -900.0, 2900.0],
           [200.0, 900.0, -200.0, 900.0, 0.0, 300.0, -300.0, 500.0]]


def _realistic_features(i):
    return [0.05 * ((i * 7) % 13) / 13 - 0.025 + 0.001 * i,
            0.04 * ((i * 3) % 11) / 11 - 0.02,
            0.05 * ((i * 5) % 17) / 17 - 0.025,
            0.04 * ((i * 11) % 7) / 7 - 0.02,
            0.2 + 0.01 * ((i * 13) % 5),
            0.05 + 0.005 * ((i * 17) % 3),
            0.2 + 0.01 * ((i * 19) % 7)]


def _realistic_samples():
    out = []
    for i in range(32):
        f = _realistic_features(i)
        x, y = map_to_screen(f, _REAL_M)
        out.append((f, x, y))
    return out


class TestCalibration(unittest.TestCase):
    def test_fit_recovers_matrix(self):
        samples = []
        for i in range(12):
            f = synth_features(i)
            x, y = map_to_screen(f, TRUE_M)
            samples.append((f, x, y))
        m = fit_calibration(samples, ridge_alpha=1e-4)
        for i in range(12):
            f = synth_features(i + 100)
            x0, y0 = map_to_screen(f, TRUE_M)
            x1, y1 = map_to_screen(f, m)
            self.assertAlmostEqual(x1, x0, delta=0.01)  # ridge bias is sub-pixel
            self.assertAlmostEqual(y1, y0, delta=0.01)

    def test_needs_five_samples(self):
        with self.assertRaises(ValueError):
            fit_calibration([([0, 0, 0, 0], 1.0, 2.0)] * 4)

    def test_grid_in_bounds(self):
        pts = calibration_points(1920, 1080)
        self.assertEqual(len(pts), 16)
        for x, y in pts:
            self.assertTrue(0 <= x <= 1920)
            self.assertTrue(0 <= y <= 1080)

    def test_dot_schedule(self):
        self.assertEqual(dot_schedule(600.0), [120.0, 240.0, 360.0, 480.0])
        self.assertEqual(dot_schedule(60.0), [])

    def test_dot_error(self):
        self.assertAlmostEqual(dot_error((100.0, 100.0), (130.0, 140.0)), 50.0)

    def test_head_motion_does_not_invert(self):
        # Regression (beta-160434): with alpha=1 the fit put +-5-11k cancelling
        # coefficients on eye vs head columns. Eye-led gaze worked, head-led
        # gaze inverted (look right -> highlight left). Strong group ridge
        # keeps the head-only response small; the eye channel carries gaze.
        samples = []
        for i in range(32):
            f = _realistic_features(i)
            # Truth: x follows the eye channel only (mirrored camera: looking
            # right decreases dx), head has NO true effect, but head covaries
            # with gaze in the samples (people turn toward targets).
            x = 2900 - 4000 * f[2] + 0 * f[4]
            y = 500 + 3000 * f[3]
            samples.append((f, x, y))
        m = fit_calibration(samples)
        f0 = list(samples[0][0])
        x0, _ = map_to_screen(f0, m)
        fh = list(f0)
        fh[4] += 0.10  # head turns, eyes fixed in orbit
        xh, _ = map_to_screen(fh, m)
        self.assertLess(abs(xh - x0), 120.0)
        fe = list(f0)
        fe[0] -= 0.03
        fe[2] -= 0.03  # eyes look right (mirrored sign)
        xe, _ = map_to_screen(fe, m)
        self.assertGreater(xe - x0, 60.0)

    def test_noisy_fit_stays_bounded(self):
        # Regression: raw normal equations on unscaled features amplified
        # live jitter (~0.02) into hundred-px jumps (beta session 20261028).
        m = fit_calibration(_realistic_samples())
        f0 = _realistic_features(3)
        x0, y0 = map_to_screen(f0, m)
        f1 = list(f0)
        f1[0] += 0.02
        x1, y1 = map_to_screen(f1, m)
        drift = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        self.assertLess(drift, 60.0)
        for i in range(32):
            f = _realistic_features(i)
            xe, ye = map_to_screen(f, _REAL_M)
            xg, yg = map_to_screen(f, m)
            # Strong default ridge (25) trades ~40px bias for bounded noise
            # gain and no head-led inversion; keys are ~190px pitch.
            self.assertLess(abs(xg - xe) + abs(yg - ye), 60.0)


if __name__ == "__main__":
    unittest.main()
