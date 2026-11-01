"""T12: mask centroid math. Parser-dependent test skips without the package."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anchors.sam_decode import box_centroid

try:
    import meta_sam_parser  # noqa: F401

    HAS_PARSER = True
except ImportError:
    HAS_PARSER = False


class TestCentroid(unittest.TestCase):
    def test_box_centroid(self):
        self.assertEqual(box_centroid(1177, 89, 1216, 105), (1196.5, 97.0))

    @unittest.skipUnless(HAS_PARSER, "meta_sam_parser not installed in this shell")
    def test_mask_centroid_live_shape(self):
        from anchors.sam_decode import mask_centroid

        class Bounds:
            left, top, right, bottom = 1177, 89, 1216, 105

        class Mask:
            width, height = 39, 16

        class Rec:
            bounds = Bounds()
            mask = Mask()

        # 559-px cross shape stand-in: exact raster math is covered by the
        # official package suite; here we check the bounds-offset contract.
        import anchors.sam_decode as d

        orig = d.decode_mask_to_raster
        try:
            d.decode_mask_to_raster = lambda m: bytes(
                1 if (x - 19) ** 2 + (y - 8) ** 2 < 25 else 0
                for y in range(16) for x in range(39)
            )
            cx, cy = mask_centroid(Rec())
        finally:
            d.decode_mask_to_raster = orig
        self.assertAlmostEqual(cx, 1177 + 19.0, delta=1.0)
        self.assertAlmostEqual(cy, 89 + 8.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
