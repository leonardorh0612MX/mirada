"""Spark proposal parsing contract (point required)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anchors.spark import parse_proposal


class TestParseProposal(unittest.TestCase):
    def test_full(self):
        out = parse_proposal('{"concept": "blue Send button", "confidence": 0.8,'
                             ' "reason": "typing", "x": 640, "y": 360}')
        self.assertEqual(out, ("blue Send button", 0.8, "typing", 640.0, 360.0))

    def test_no_point_rejected(self):
        self.assertIsNone(parse_proposal('{"concept": "button", "confidence": 0.9}'))

    def test_garbage_rejected(self):
        self.assertIsNone(parse_proposal("blank black screen"))
        self.assertIsNone(parse_proposal(""))


if __name__ == "__main__":
    unittest.main()
