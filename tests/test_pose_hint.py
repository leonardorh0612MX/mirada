"""Pose hint directions. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.beta import pose_hint

REF = {"nose": (640.0, 360.0), "fw": 200.0}


class TestPoseHint(unittest.TestCase):
    def test_aligned(self):
        self.assertEqual(pose_hint(REF, (640.0, 360.0), 200.0), "")

    def test_nose_drifted_image_right_tells_user_right(self):
        self.assertIn("RIGHT", pose_hint(REF, (700.0, 360.0), 200.0))

    def test_nose_drifted_image_left_tells_user_left(self):
        self.assertIn("LEFT", pose_hint(REF, (580.0, 360.0), 200.0))

    def test_moved_down_tells_up(self):
        self.assertIn("UP", pose_hint(REF, (640.0, 420.0), 200.0))

    def test_too_far_tells_closer(self):
        self.assertIn("CLOSER", pose_hint(REF, (640.0, 360.0), 150.0))

    def test_missing(self):
        self.assertEqual(pose_hint({"nose": None, "fw": None}, None, 0), "")


if __name__ == "__main__":
    unittest.main()
