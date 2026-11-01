"""T5: gaze features on a synthetic landmark fixture. Stdlib only."""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.features import extract_features, map_to_screen


def make_landmarks(dx=0.0, nose_x=170.0):
    """478 points, eyes 40 px wide, iris shifted dx, face box 200x260."""
    pts = [(0.0, 0.0)] * 478
    pts = [list(p) for p in pts]
    pts[33] = [100.0, 200.0]
    pts[133] = [140.0, 200.0]
    pts[362] = [200.0, 200.0]
    pts[263] = [240.0, 200.0]
    for i in (468, 469, 470, 471, 472):
        pts[i] = [120.0 + dx, 200.0]
    for i in (473, 474, 475, 476, 477):
        pts[i] = [220.0 + dx, 200.0]
    pts[234] = [70.0, 260.0]   # cheek L
    pts[454] = [270.0, 260.0]  # cheek R
    pts[10] = [170.0, 70.0]    # forehead
    pts[152] = [170.0, 330.0]  # chin
    pts[1] = [nose_x, 240.0]   # nose tip
    return [tuple(p) for p in pts]


class TestFeatures(unittest.TestCase):
    def test_valid_centered(self):
        feats, valid, reason = extract_features(make_landmarks())
        self.assertTrue(valid, reason)
        self.assertEqual(reason, "ok")
        self.assertEqual(len(feats), 7)
        for v in feats:
            self.assertTrue(-1.0 < v < 1.0)

    def test_head_turn_moves_yaw(self):
        f0, _, _ = extract_features(make_landmarks(nose_x=170.0))
        f1, _, _ = extract_features(make_landmarks(nose_x=190.0))
        self.assertAlmostEqual(f1[4] - f0[4], 20.0 / 200.0)  # head_dx
        self.assertAlmostEqual(f1[0], f0[0])  # eyes unchanged

    def test_shift_moves_features(self):
        f0, _, _ = extract_features(make_landmarks(dx=0.0))
        f1, _, _ = extract_features(make_landmarks(dx=4.0))
        self.assertGreater(f1[0], f0[0])
        self.assertGreater(f1[2], f0[2])
        self.assertAlmostEqual(f1[0] - f0[0], 4.0 / 40.0)

    def test_no_face_invalid(self):
        feats, valid, reason = extract_features([])
        self.assertFalse(valid)
        self.assertEqual(reason, "no_face")
        self.assertIsNone(feats)

    def test_short_invalid(self):
        feats, valid, reason = extract_features([(0.0, 0.0)] * 10)
        self.assertFalse(valid)
        self.assertEqual(reason, "short_landmarks")

    def test_degenerate_eye_invalid(self):
        pts = make_landmarks()
        pts = [list(p) for p in pts]
        pts[33] = [140.0, 200.0]  # collapse left eye width to zero
        feats, valid, reason = extract_features([tuple(p) for p in pts])
        self.assertFalse(valid)
        self.assertEqual(reason, "degenerate_eye")

    def test_map_identity(self):
        m = [[1.0, 0.0, 0.0, 0.0, 960.0], [0.0, 1.0, 0.0, 0.0, 540.0]]
        x, y = map_to_screen([0.1, 0.2, 0.1, 0.2], m)
        self.assertAlmostEqual(x, 960.1)
        self.assertAlmostEqual(y, 540.2)


if __name__ == "__main__":
    unittest.main()
