"""Factorial enrollment plan: structure, poses, repeat block."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.board import enrollment_plan, natural_block_indices


class TestEnrollmentPlan(unittest.TestCase):
    def test_shape_and_blocks(self):
        plan = enrollment_plan()
        self.assertEqual(len(plan), 43)  # A9 + B25 + E9
        a, b, e = plan[:9], plan[9:34], plan[34:]
        self.assertEqual([(x, y) for x, y, _ in a],
                         [(x, y) for x, y, _ in e])  # E repeats A
        poses = {msg.split(" ·")[0] for _, _, msg in b}
        self.assertEqual(len(poses), 5)
        self.assertEqual(len(b), 25)

    def test_natural_indices(self):
        self.assertEqual(natural_block_indices(43),
                         list(range(9)) + list(range(34, 43)))
        self.assertEqual(natural_block_indices(10), list(range(10)))

    def test_fractions_inside_screen(self):
        for fx, fy, msg in enrollment_plan():
            self.assertTrue(0.0 < fx < 1.0 and 0.0 < fy < 1.0)
            self.assertTrue(msg)


if __name__ == "__main__":
    unittest.main()
