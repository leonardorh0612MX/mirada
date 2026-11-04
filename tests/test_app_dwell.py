"""App-mode dwell click: rest-to-click, move resets, refractory gaps.

Blink-hold clicks fired while reading Discord (web-20261101-230023:
11 clicks, no intent). Stdlib only.
"""
import unittest

from app.board_web import AppDwell, fresh_median, tile_hold_target


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


class TestTileHold(unittest.TestCase):
    # Gaze dwell (0.8 s, eyes open) never completes on the small
    # corner tiles, so a look+close hold aimed at one must fire it -
    # same grammar as the board. Rects are absolute, [back, kb].
    RECTS = [(2712, 16, 200, 124), (2924, 16, 200, 124)]

    def test_hold_on_kb_fires_keyboard(self):
        self.assertEqual(tile_hold_target(3000, 80, self.RECTS), "kb")

    def test_hold_on_back_returns(self):
        self.assertEqual(tile_hold_target(2800, 80, self.RECTS), "back")

    def test_hold_on_gap_clicks_nothing(self):
        self.assertIsNone(tile_hold_target(2918, 80, self.RECTS))

    def test_hold_far_above_tiles_clicks_nothing(self):
        # D41's strict rects expected None 8 px above the tile; D42
        # widens with a margin (edge error eats strict edges), so a
        # near-miss fires (see near_tile test) and only a far hold
        # stays silent.
        self.assertIsNone(tile_hold_target(3000, -60, self.RECTS))

    def test_no_rects_clicks_nothing(self):
        self.assertIsNone(tile_hold_target(3000, 80, None))
        self.assertIsNone(tile_hold_target(3000, 80, []))

    def test_edges_count_as_inside(self):
        self.assertEqual(tile_hold_target(2924, 16, self.RECTS), "kb")
        self.assertEqual(tile_hold_target(3124, 140, self.RECTS), "kb")

    def test_hold_near_tile_within_margin_fires(self):
        # 8 px above the kb tile: aiming at it, edge error eats the
        # strict edge. The 60 px margin catches genuine attempts.
        self.assertEqual(tile_hold_target(3000, 8, self.RECTS), "kb")

    def test_hold_beyond_margin_clicks_nothing(self):
        self.assertIsNone(tile_hold_target(2612, 80, self.RECTS))

    def test_strict_beats_margin_on_overlap(self):
        # Strictly inside kb, yet inside back's margin too: the
        # point belongs to kb.
        self.assertEqual(tile_hold_target(2950, 80, self.RECTS), "kb")

    def test_gap_stays_dead_with_margin(self):
        # The inflated rects overlap the gap; the strip between the
        # tiles is ambiguous by construction, so it fires nothing.
        self.assertIsNone(tile_hold_target(2918, 160, self.RECTS))


class TestFreshMedian(unittest.TestCase):
    # Tile routing must use the CURRENT fixation (median over
    # [now-0.5, now-0.15]), not the lagged click point (median over
    # [now-0.9, now-0.45]): routing on the lagged point fired the
    # tile the user had JUST LEFT (Nov 4: video hold opened the
    # keyboard, tile hold clicked the video).
    NOW = 100.0

    def test_window_skips_stale_and_closing(self):
        hist = [(99.0, 0, 0),           # too old
                (99.6, 100, 100), (99.7, 110, 90),  # in window
                (99.97, 500, 500)]      # too new (closing smear?)
        self.assertEqual(fresh_median(hist, self.NOW), (110, 100))

    def test_boundaries_included(self):
        hist = [(99.5, 10, 20), (99.85, 30, 40)]
        self.assertEqual(fresh_median(hist, self.NOW), (30, 40))

    def test_empty_window_is_none(self):
        self.assertIsNone(fresh_median([(90.0, 1, 1)], self.NOW))
        self.assertIsNone(fresh_median([], self.NOW))


if __name__ == "__main__":
    unittest.main()
