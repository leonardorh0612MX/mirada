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
        from app.board_app import in_rect, overlay_rect

        r = overlay_rect(1920, 1080)
        self.assertEqual(r, (1920 - 476, 16, 440, 210))
        self.assertTrue(in_rect(1700, 100, r))
        self.assertFalse(in_rect(100, 100, r))
        self.assertFalse(in_rect(1700, 900, r))

    def test_monitor_rect_clamps(self):
        from app.board_app import monitor_rect

        mons = [(0, 0, 1920, 1200), (1920, 0, 1920, 1080)]
        self.assertEqual(monitor_rect(mons, 1), (1920, 0, 1920, 1080))
        self.assertEqual(monitor_rect(mons, 9), (1920, 0, 1920, 1080))
        self.assertEqual(monitor_rect(mons, -1), (0, 0, 1920, 1200))
        self.assertEqual(monitor_rect([], 0), (0, 0, 1280, 800))


if __name__ == "__main__":
    unittest.main()
