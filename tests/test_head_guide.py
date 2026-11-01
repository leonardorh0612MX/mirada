"""head_view: ceremony ellipse math (target zone checked, not measured)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.board import guide_reference, head_view, pose_inside


def face(fx=0.5, fy=0.5, fw=0.30):
    lms = [(0.0, 0.0)] * 478
    lms = [[0.0, 0.0] for _ in range(478)]
    cx, cy = fx * 1280, fy * 720
    lms[234] = [cx - fw * 1280 / 2, cy]
    lms[454] = [cx + fw * 1280 / 2, cy]
    lms[10] = [cx, cy - 0.2 * 720]
    lms[152] = [cx, cy + 0.2 * 720]
    return lms


class TestHeadView(unittest.TestCase):
    def test_centered_face_inside(self):
        ex, ey, rx, ry, inside = head_view(face(), 1920, 1080)
        self.assertTrue(inside)
        self.assertAlmostEqual(ex, 960, places=0)
        self.assertAlmostEqual(ey, 540, places=0)

    def test_side_face_outside(self):
        _, _, _, _, inside = head_view(face(fx=0.75), 1920, 1080)
        self.assertFalse(inside)

    def test_tiny_face_outside(self):
        _, _, _, _, inside = head_view(face(fw=0.08), 1920, 1080)
        self.assertFalse(inside)

    def test_offcenter_comfortable_pose_inside(self):
        # The web-230837 case: natural pose sits off-center with fw 0.20.
        ref = (0.38, 0.62, 0.20)
        lms = face(fx=0.38, fy=0.62, fw=0.20)
        _, _, _, _, inside = head_view(lms, 1920, 1080, ref=ref)
        self.assertTrue(inside)
        self.assertTrue(pose_inside(0.40, 0.60, 0.21, ref))
        self.assertFalse(pose_inside(0.50, 0.50, 0.20, ref))

    def test_reference_is_median(self):
        samples = [(0.40, 0.50, 0.20), (0.60, 0.50, 0.22), (0.41, 0.50, 0.21)]
        self.assertEqual(guide_reference(samples), (0.41, 0.50, 0.21))
        self.assertEqual(guide_reference([]), (0.5, 0.45, 0.20))


if __name__ == "__main__":
    unittest.main()
