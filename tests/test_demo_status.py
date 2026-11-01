"""T15: demo status transitions and recovery. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.demo_status import API_DOWN, LOW_LIGHT, NO_FACE, OK, DemoStatus


class TestDemoStatus(unittest.TestCase):
    def test_healthy_is_ok(self):
        s = DemoStatus()
        self.assertEqual(s.update(True, 120.0, True, 0.0), OK)
        self.assertFalse(s.banner)

    def test_face_grace_then_lost(self):
        s = DemoStatus(face_grace_s=1.5)
        s.update(True, 120.0, True, 0.0)
        self.assertEqual(s.update(False, 120.0, True, 1.0), OK)  # within grace
        self.assertEqual(s.update(False, 120.0, True, 2.0), NO_FACE)
        self.assertTrue(s.banner)
        self.assertIn("face", s.message.lower())

    def test_face_recovery(self):
        s = DemoStatus()
        s.update(False, 120.0, True, 5.0)
        self.assertEqual(s.state, NO_FACE)
        self.assertEqual(s.update(True, 120.0, True, 6.0), OK)

    def test_low_light(self):
        s = DemoStatus(brightness_threshold=40.0)
        self.assertEqual(s.update(True, 20.0, True, 0.0), LOW_LIGHT)
        self.assertEqual(s.update(True, 60.0, True, 1.0), OK)

    def test_api_down_wins_over_face(self):
        s = DemoStatus()
        # Never saw a face and API down: API state takes priority.
        self.assertEqual(s.update(False, 120.0, False, 0.0), API_DOWN)

    def test_api_recovery(self):
        s = DemoStatus()
        s.update(True, 120.0, False, 0.0)
        self.assertEqual(s.update(True, 120.0, True, 1.0), OK)


if __name__ == "__main__":
    unittest.main()
