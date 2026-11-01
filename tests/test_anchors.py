"""T10/T12: ledger verdicts and SAM lane parsing. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anchors.ledger import AnchorLedger, make_anchor
from anchors.sam_lane import box_centroid, parse_lane, to_screen_pixels

# Real lane fragment shape from the Oct 27 SAM probe (mask payload shortened).
REAL_LANE = (
    "<0f>0<|box;x1=1169;y1=737;x2=1181;y2=749;w=1280;h=800|>"
    "<|mask;x=0;y=0;data=13,13,~!!!!j!0g|>,"
    "1<|box;x1=11;y1=154;x2=37;y2=181;w=1280;h=800|>"
    "<|mask;x=0;y=0;data=28,27,~!!!$Z!0g|>"
)


class TestLedger(unittest.TestCase):
    def test_propose_resolve(self):
        ledger = AnchorLedger()
        aid = ledger.propose(make_anchor("spark", 100.0, 200.0, 0.8, "caret", 1.0))
        ledger.resolve(aid, True, "applied")
        self.assertEqual(len(ledger.accepted()), 1)

    def test_unknown_id(self):
        with self.assertRaises(KeyError):
            AnchorLedger().resolve(999, True, "x")

    def test_precision(self):
        ledger = AnchorLedger()
        a1 = ledger.propose(make_anchor("sam", 100.0, 100.0, 0.9, "t", 1.0))
        a2 = ledger.propose(make_anchor("sam", 500.0, 500.0, 0.9, "t", 2.0))
        ledger.resolve(a1, True, "applied")
        ledger.resolve(a2, True, "applied")
        gt = {a1: (102.0, 101.0), a2: (900.0, 900.0)}
        self.assertAlmostEqual(ledger.precision(gt, 50.0), 0.5)


class TestSamLane(unittest.TestCase):
    def test_real_lane(self):
        recs = parse_lane(REAL_LANE)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["object_id"], 0)
        self.assertEqual(recs[0]["box"], (1169, 737, 1181, 749))
        self.assertEqual(recs[0]["frame_size"], (1280, 800))
        self.assertIsNone(recs[0]["confidence"])

    def test_empty_lane(self):
        self.assertEqual(parse_lane(""), [])
        self.assertEqual(parse_lane("   "), [])

    def test_bad_frame(self):
        with self.assertRaises(ValueError):
            parse_lane("<3f>0<|box;x1=1;y1=1;x2=2;y2=2;w=9;h=9|>")

    def test_centroid_and_scale(self):
        cx, cy = box_centroid((1169, 737, 1181, 749))
        self.assertAlmostEqual(cx, 1175.0)
        self.assertAlmostEqual(cy, 743.0)
        # Thumbnail 1280x800 sent, source monitor 2560x1600 at offset (1920, 0).
        sx, sy = to_screen_pixels((cx, cy), (1280, 800), (2560, 1600), (1920, 0))
        self.assertAlmostEqual(sx, 1175.0 * 2 + 1920)
        self.assertAlmostEqual(sy, 743.0 * 2)


if __name__ == "__main__":
    unittest.main()
