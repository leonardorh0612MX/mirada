"""Environment estimate math: distance and light labels. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.env_check import estimate_distance_cm, expected_conditions, light_label


class TestEnvCheck(unittest.TestCase):
    def test_distance_scales_inverse(self):
        d1 = estimate_distance_cm(200, 1280)
        d2 = estimate_distance_cm(400, 1280)
        self.assertAlmostEqual(d2, d1 / 2, places=6)
        self.assertGreater(d1, 40)
        self.assertLess(d1, 80)

    def test_bad_input(self):
        self.assertIsNone(estimate_distance_cm(0, 1280))

    def test_labels(self):
        self.assertEqual(light_label(30), "dark")
        self.assertEqual(light_label(80), "ok")

    def test_warnings(self):
        self.assertTrue(expected_conditions(30, 55))
        self.assertEqual(expected_conditions(90, 60), [])


if __name__ == "__main__":
    unittest.main()
