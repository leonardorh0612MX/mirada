"""Board keyboard page: Spanish layout geometry and typing reducer."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.keyboard_layout import board_keyboard, type_text


class TestBoardKeyboard(unittest.TestCase):
    def test_layout_inside_band_with_enye(self):
        keys = board_keyboard(1920, 100, 700)
        labels = [k["label"] for k in keys]
        self.assertIn("Ñ", labels)
        self.assertIn("SPACE", labels)
        self.assertIn("DELETE", labels)
        for k in keys:
            x1, y1, x2, y2 = k["rect"]
            self.assertTrue(0 <= x1 < x2 <= 1920)
            self.assertTrue(100 <= y1 < y2 <= 800)

    def test_keys_are_gaze_sized(self):
        keys = board_keyboard(1920, 100, 700)
        h_key = next(k for k in keys if k["label"] == "H")
        self.assertGreater(h_key["rect"][2] - h_key["rect"][0], 140)

    def test_type_text(self):
        self.assertEqual(type_text("", "H"), "h")
        self.assertEqual(type_text("hol", "A"), "hola")
        self.assertEqual(type_text("hola", "SPACE"), "hola ")
        self.assertEqual(type_text("hola ", "DELETE"), "hola")
        self.assertEqual(type_text("hola", "hola"), "hola")  # sug: no-op here


if __name__ == "__main__":
    unittest.main()
