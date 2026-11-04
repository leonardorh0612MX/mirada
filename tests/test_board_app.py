"""Native app wrapper reuses the verified web engine, never forks it."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBoardApp(unittest.TestCase):
    def test_reuses_board_web_engine(self):
        import app.board_app as app_mod
        import app.board_web as web_mod

        self.assertIs(app_mod.engine, web_mod.engine)
        self.assertIs(app_mod.Handler, web_mod.Handler)
        self.assertIs(app_mod.Server, web_mod.Server)

    def test_overlay_rect_top_right(self):
        from app.board_app import in_rect, overlay_rect, tile_rects

        r = overlay_rect(1920, 1080)
        self.assertEqual(r, (1920 - 428, 16, 412, 124))
        self.assertTrue(in_rect(1700, 100, r))
        self.assertFalse(in_rect(100, 100, r))
        self.assertFalse(in_rect(1700, 900, r))
        back, kb = tile_rects(1920, 1080)
        self.assertEqual(back, (1920 - 428, 16, 200, 124))
        self.assertEqual(kb, (1920 - 428 + 212, 16, 200, 124))
        # Both tiles inside the bbox, with a clickable gap between.
        self.assertTrue(in_rect(1700, 100, r))
        self.assertFalse(in_rect(back[0] + 205, 100, back))
        self.assertFalse(in_rect(back[0] + 205, 100, kb))

    def test_render_tile_shape(self):
        from app.board_app import TILE_H, TILE_W, render_tile

        img = render_tile("MIRADA", "BACK", "\u2190")
        self.assertEqual(img.size, (TILE_W, TILE_H))
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.getpixel((0, 0)), (255, 0, 255))
        cx, cy = TILE_W // 2, TILE_H // 2
        self.assertNotEqual(img.getpixel((cx, cy)), (255, 0, 255))

    def test_render_tile_has_no_pink_fringe(self):
        # Regression (Nov 3): soft-alpha edges blended against the
        # magenta label and printed as pink particles. The silhouette
        # is hard now: no near-magenta pixel may survive.
        from app.board_app import render_tile

        img = render_tile("MIRADA", "BACK", "\u2190")
        fringe = [px for px in img.getdata()
                  if px != (255, 0, 255)
                  and px[0] > 120 and px[2] > 120 and px[1] < 120]
        self.assertEqual(fringe, [])

    def test_render_ring_shape(self):
        from app.board_app import render_ring

        img = render_ring(0.0)
        self.assertEqual(img.size, (120, 120))
        self.assertEqual(img.mode, "RGB")
        self.assertEqual(img.getpixel((0, 0)), (255, 0, 255))
        # White centre dot survives the flattening.
        self.assertEqual(img.getpixel((60, 60)), (255, 255, 255))

    def test_render_ring_arc_and_no_fringe(self):
        from app.board_app import render_ring

        plain = render_ring(0.0)
        arc = render_ring(0.5)
        self.assertNotEqual(list(plain.getdata()), list(arc.getdata()))
        fringe = [px for px in arc.getdata()
                  if px != (255, 0, 255)
                  and px[0] > 120 and px[2] > 120 and px[1] < 120]
        self.assertEqual(fringe, [])

    def test_monitor_rect_clamps(self):
        from app.board_app import monitor_rect

        mons = [(0, 0, 1920, 1200), (1920, 0, 1920, 1080)]
        self.assertEqual(monitor_rect(mons, 1), (1920, 0, 1920, 1080))
        self.assertEqual(monitor_rect(mons, 9), (1920, 0, 1920, 1080))
        self.assertEqual(monitor_rect(mons, -1), (0, 0, 1920, 1200))
        self.assertEqual(monitor_rect([], 0), (0, 0, 1280, 800))

    def test_tile_dwell_enter_fire(self):
        from app.board_app import tile_dwell_next

        mem = {"zone": None, "since": 0.0, "pending": None,
               "pending_since": 0.0}
        ev, mem = tile_dwell_next(mem, "kb", 10.0)
        self.assertIsNone(ev)  # entering grace, not yet armed
        ev, mem = tile_dwell_next(mem, "kb", 10.13)
        self.assertEqual(ev, "started")
        ev, mem = tile_dwell_next(mem, "kb", 10.5)
        self.assertIsNone(ev)
        ev, mem = tile_dwell_next(mem, "kb", 10.94)
        self.assertEqual(ev, "fired")

    def test_tile_dwell_edge_jitter_keeps_timer(self):
        # Regression (Nov 3): 7 stillborn "kb started" in a row -
        # border flicker restarted the 0.8 s timer forever.
        from app.board_app import tile_dwell_next

        mem = {"zone": None, "since": 0.0, "pending": None,
               "pending_since": 0.0}
        _, mem = tile_dwell_next(mem, "kb", 10.0)
        ev, mem = tile_dwell_next(mem, "kb", 10.13)
        self.assertEqual(ev, "started")
        ev, mem = tile_dwell_next(mem, None, 10.5)  # brief flicker out
        self.assertIsNone(ev)
        self.assertEqual(mem["zone"], "kb")
        ev, mem = tile_dwell_next(mem, "kb", 10.6)
        self.assertIsNone(ev)  # no second "started"
        ev, _mem = tile_dwell_next(mem, "kb", 10.95)
        self.assertEqual(ev, "fired")

    def test_tile_dwell_leaves_after_grace(self):
        from app.board_app import tile_dwell_next

        mem = {"zone": "kb", "since": 10.0, "pending": None,
               "pending_since": 0.0}
        ev, mem = tile_dwell_next(mem, None, 10.5)
        self.assertIsNone(ev)
        self.assertEqual(mem["zone"], "kb")
        ev, mem = tile_dwell_next(mem, None, 10.9)
        self.assertIsNone(ev)
        self.assertIsNone(mem["zone"])


if __name__ == "__main__":
    unittest.main()
