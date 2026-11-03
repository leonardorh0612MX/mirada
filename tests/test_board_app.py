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
        self.assertEqual(img.mode, "RGBA")
        self.assertEqual(img.getpixel((0, 0))[3], 0)  # round corners
        cx, cy = TILE_W // 2, TILE_H // 2
        self.assertEqual(img.getpixel((cx, cy))[3], 255)  # solid body

    def test_monitor_rect_clamps(self):
        from app.board_app import monitor_rect

        mons = [(0, 0, 1920, 1200), (1920, 0, 1920, 1080)]
        self.assertEqual(monitor_rect(mons, 1), (1920, 0, 1920, 1080))
        self.assertEqual(monitor_rect(mons, 9), (1920, 0, 1920, 1080))
        self.assertEqual(monitor_rect(mons, -1), (0, 0, 1920, 1200))
        self.assertEqual(monitor_rect([], 0), (0, 0, 1280, 800))


if __name__ == "__main__":
    unittest.main()
