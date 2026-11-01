"""Coverage gate: convex hull of enrollment targets. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.coverage import convex_hull, inside_hull


class TestCoverage(unittest.TestCase):
    def test_hull_square(self):
        h = convex_hull([(0, 0), (10, 0), (10, 10), (0, 10), (5, 5)])
        self.assertEqual(len(h), 4)
        self.assertTrue(inside_hull((5, 5), h))
        self.assertFalse(inside_hull((20, 5), h))

    def test_degenerate(self):
        self.assertTrue(inside_hull((99, 99), convex_hull([(1, 1)])))

    def test_margin_shrinks(self):
        h = convex_hull([(0, 0), (100, 0), (100, 100), (0, 100)])
        self.assertTrue(inside_hull((2, 50), h, margin=0.0))
        self.assertFalse(inside_hull((2, 50), h, margin=10.0))
        self.assertTrue(inside_hull((50, 50), h, margin=10.0))


if __name__ == "__main__":
    unittest.main()
