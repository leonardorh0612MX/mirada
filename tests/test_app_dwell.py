"""App-mode dwell click: rest-to-click, move resets, refractory gaps.

Blink-hold clicks fired while reading Discord (web-20261101-230023:
11 clicks, no intent). Stdlib only.
"""
import unittest

from app.board_web import AppDwell


class TestAppDwell(unittest.TestCase):
    def test_rest_fires(self):
        d = AppDwell(radius_px=100.0, dwell_s=0.9, refractory_s=1.5)
        self.assertFalse(d.update(0, 0, 0.0))
        self.assertFalse(d.update(5, 5, 0.5))
        self.assertTrue(d.update(5, 5, 0.91))

    def test_move_resets(self):
        d = AppDwell(radius_px=100.0, dwell_s=0.9, refractory_s=1.5)
        d.update(0, 0, 0.0)
        self.assertFalse(d.update(500, 500, 0.8))  # moved: restart
        self.assertFalse(d.update(500, 500, 1.5))  # only 0.7 s in
        self.assertTrue(d.update(500, 500, 1.75))

    def test_refractory_blocks_repeats(self):
        d = AppDwell(radius_px=100.0, dwell_s=0.5, refractory_s=1.5)
        d.update(0, 0, 0.0)
        self.assertTrue(d.update(0, 0, 0.6))
        self.assertFalse(d.update(0, 0, 1.0))  # inside refractory
        self.assertFalse(d.update(0, 0, 2.2))  # new anchor after
        self.assertTrue(d.update(0, 0, 2.8))

    def test_reset_clears_anchor(self):
        d = AppDwell(radius_px=100.0, dwell_s=0.5, refractory_s=1.5)
        d.update(0, 0, 0.0)
        d.reset()  # over the floating dock: watcher owns the click
        self.assertFalse(d.update(0, 0, 0.6))

    def test_click_lands_on_centroid_not_live_point(self):
        # The live point wanders even when the eye is still; the click
        # must land on the rest centroid.
        d = AppDwell(radius_px=100.0, dwell_s=0.5, refractory_s=1.5)
        d.update(0, 0, 0.0)
        d.update(10, 0, 0.2)
        d.update(0, 10, 0.4)
        self.assertTrue(d.update(10, 10, 0.6))
        self.assertEqual(d.centroid, (5.0, 5.0))

    def test_progress_ramps_then_holds_zero_in_refractory(self):
        d = AppDwell(radius_px=100.0, dwell_s=1.0, refractory_s=1.5)
        d.update(0, 0, 0.0)
        d.update(0, 0, 0.5)
        self.assertAlmostEqual(d.progress(0.5), 0.5)
        self.assertTrue(d.update(0, 0, 1.0))
        self.assertEqual(d.progress(1.2), 0.0)
        self.assertIsNone(AppDwell().centroid)


if __name__ == "__main__":
    unittest.main()
