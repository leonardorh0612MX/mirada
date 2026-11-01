"""Board geometry: display bar top, function row bottom, no overlaps."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.board import phrase_area, strip_layout


def overlap(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2


class TestStripLayout(unittest.TestCase):
    def test_order_no_overlap_inside_screen(self):
        for mw, mh in ((1920, 1080), (1366, 768)):
            funcs, bar = strip_layout(mw, mh)
            labels = [c["label"] for c in funcs]
            self.assertEqual(labels, ["RECAL", "SPEAK", "CLEAR", "SETTINGS",
                                      "QUIT"])
            rects = [c["rect"] for c in funcs] + [bar]
            for r in rects:
                self.assertGreaterEqual(r[0], 0)
                self.assertGreaterEqual(r[1], 0)
                self.assertLessEqual(r[2], mw)
                self.assertLessEqual(r[3], mh)
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    self.assertFalse(overlap(rects[i], rects[j]),
                                     f"{mw}x{mh} {i} vs {j}")
            for c in funcs:
                x1, y1, x2, y2 = c["rect"]
                self.assertGreater(x2 - x1, 150)
                self.assertGreater(y2 - y1, 120)

    def test_phrase_area_clear_of_bar_and_funcs(self):
        for mw, mh in ((1920, 1080), (1366, 768)):
            funcs, bar = strip_layout(mw, mh)
            y0, y1 = phrase_area(mh)
            self.assertGreater(y0, bar[3])
            self.assertLess(y1, min(c["rect"][1] for c in funcs))
            self.assertGreater(y1 - y0, 300)


if __name__ == "__main__":
    unittest.main()
