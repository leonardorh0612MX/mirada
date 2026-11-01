"""Appearance vectors (geometry matches training) and tuple samples."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from corrector.corrector import BiasCorrector
from gaze.appearance import LEFT_IDS, RIGHT_IDS, ridge_fit, ridge_predict, vector_from_frame


def fake_face(w=160, h=120):
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:, :, 1] = 128
    lms = [(0.0, 0.0)] * 478
    lms = [[0.0, 0.0] for _ in range(478)]
    lx = [30 + i * 3 for i in range(7)]
    ly = [50 + (i % 3) for i in range(7)]
    for j, i in enumerate(LEFT_IDS):
        lms[i] = [float(lx[j]), float(ly[j])]
    rx = [100 + i * 3 for i in range(7)]
    ry = [50 + (i % 3) for i in range(7)]
    for j, i in enumerate(RIGHT_IDS):
        lms[i] = [float(rx[j]), float(ry[j])]
    return frame, lms


class TestAppearanceVector(unittest.TestCase):
    def test_shape_range_deterministic(self):
        frame, lms = fake_face()
        v1 = vector_from_frame(frame, lms)
        v2 = vector_from_frame(frame.copy(), [p[:] for p in lms])
        self.assertEqual(v1.shape, (768,))
        self.assertTrue(bool(np.all(v1 >= 0.0) and np.all(v1 <= 1.0)))
        self.assertTrue(bool(np.array_equal(v1, v2)))

    def test_degenerate_returns_none(self):
        frame = np.zeros((5, 5, 3), dtype=np.uint8)
        lms = [[2.0, 2.0] for _ in range(478)]
        self.assertIsNone(vector_from_frame(frame, lms))

    def test_ridge_recovers_map(self):
        rng = np.random.RandomState(3)
        X = rng.uniform(size=(30, 768))
        Y = np.column_stack([X[:, 0] * 500 + 100, X[:, 1] * 300 + 50])
        model = ridge_fit(X, Y, alpha=1.0)
        pred = ridge_predict(X, model)
        err = np.abs(pred - Y).mean()
        self.assertLess(err, 5.0)


class TestTupleSamples(unittest.TestCase):
    def test_certain_applies_and_moves(self):
        c = BiasCorrector(lambda s: (s[0], 100.0), [0.0] * 7,
                          sample_feats=lambda s: s[1])
        stt, _ = c.update((50.0, [0.0] * 7), (400.0, 100.0), certain=True)
        self.assertEqual(stt, "applied")
        before = c.predict((50.0, [0.0] * 7))
        c.update((50.0, [0.0] * 7), (400.0, 100.0), certain=True)
        after = c.predict((50.0, [0.0] * 7))
        self.assertLess(abs(after[0] - 400.0), abs(before[0] - 400.0))

    def test_head_comes_from_feats_half(self):
        c = BiasCorrector(lambda s: (100.0, 100.0), [0.0] * 7,
                          sample_feats=lambda s: s[1])
        f0 = [0.0] * 7
        f1 = [0.0] * 7
        f1[4] = 0.04  # one head unit off
        c.update(("v", f1), (200.0, 100.0), certain=True)
        p0 = c.predict(("v", f0))[0]
        p1 = c.predict(("v", f1))[0]
        self.assertNotAlmostEqual(p0, p1)  # head-coupled, not constant


if __name__ == "__main__":
    unittest.main()
