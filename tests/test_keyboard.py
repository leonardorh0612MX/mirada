"""T24 layout: coverage, hit-testing, large keys. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.keyboard_layout import hit_key, layout


class TestLayout(unittest.TestCase):
    def setUp(self):
        self.keys = layout(1920, 1080)

    def test_all_letters_present(self):
        labels = {k["label"] for k in self.keys}
        for ch in "QWERTYUIOPASDFGHJKLZXCVBNM":
            self.assertIn(ch, labels)
        self.assertIn("SPACE", labels)
        self.assertIn("DELETE", labels)

    def test_keys_large(self):
        for k in self.keys:
            x1, y1, x2, y2 = k["rect"]
            self.assertGreaterEqual(x2 - x1, 100)
            self.assertGreaterEqual(y2 - y1, 100)

    def test_hit_center_of_key(self):
        k = self.keys[0]
        x1, y1, x2, y2 = k["rect"]
        self.assertEqual(hit_key(self.keys, (x1 + x2) / 2, (y1 + y2) / 2), "Q")

    def test_hit_gap_is_none(self):
        self.assertIsNone(hit_key(self.keys, 2, 2))


if __name__ == "__main__":
    unittest.main()
