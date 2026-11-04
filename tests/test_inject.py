"""clamp_xy: gaze clicks stay on the monitor."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.inject import center_on_monitor, clamp_xy, to_absolute


class TestClampXy(unittest.TestCase):
    RECT = (1920, 0, 1920, 1080)

    def test_inside_point_untouched(self):
        self.assertEqual(clamp_xy(2880, 540, self.RECT), (2880, 540))

    def test_offscreen_click_clamps(self):
        # Live (Nov 3): a dwell click landed at x=3914, 74 px past the
        # 3840 edge of monitor 1.
        self.assertEqual(clamp_xy(3914, 284, self.RECT), (3839, 284))
        self.assertEqual(clamp_xy(100, 2000, self.RECT), (1920, 1079))

    def test_edges_are_inclusive(self):
        self.assertEqual(clamp_xy(1920, 0, self.RECT), (1920, 0))
        self.assertEqual(clamp_xy(3839, 1079, self.RECT), (3839, 1079))


class TestToAbsolute(unittest.TestCase):
    VS = (0, 0, 3840, 1200)  # laptop + external side by side

    def test_corners(self):
        self.assertEqual(to_absolute(0, 0, self.VS), (0, 0))
        self.assertEqual(to_absolute(3840, 1200, self.VS),
                         (65535, 65535))

    def test_midpoint_and_offset(self):
        ax, ay = to_absolute(2880, 540, self.VS)
        self.assertEqual((ax, ay), (int(2880 * 65535 / 3840),
                                   int(540 * 65535 / 1200)))
        self.assertEqual(to_absolute(-100, 6000, self.VS),
                         (0, 65535))

    def test_abs_move_maps_whole_desktop(self):
        # Regression (Nov 3): without VIRTUALDESK, absolute moves
        # map to the primary monitor only - clicks landed on the
        # laptop while the ring aimed at the external screen.
        from app import inject

        inp = inject._abs_move(100, 200)
        flags = inp.u.mi.dwFlags
        self.assertTrue(flags & inject.MOUSEEVENTF_ABSOLUTE)
        self.assertTrue(flags & inject.MOUSEEVENTF_MOVE)
        self.assertTrue(flags & inject.MOUSEEVENTF_VIRTUALDESK)
        self.assertEqual((inp.u.mi.dx, inp.u.mi.dy), (100, 200))


class TestCenterOnMonitor(unittest.TestCase):
    MON = (1920, 0, 1920, 1080)

    def test_same_monitor(self):
        self.assertTrue(center_on_monitor((2000, 100, 3000, 900),
                                          self.MON))

    def test_other_monitor(self):
        self.assertFalse(center_on_monitor((100, 100, 900, 900),
                                           self.MON))

    def test_straddling_uses_center(self):
        # Mostly on the laptop, center still left of 1920.
        self.assertFalse(center_on_monitor((1500, 100, 2300, 900),
                                           self.MON))
        self.assertTrue(center_on_monitor((1600, 100, 2500, 900),
                                          self.MON))

    def test_degenerate_point_rect(self):
        # park_cursor asks about a cursor point, not a window.
        self.assertTrue(center_on_monitor((2880, 540, 2880, 540),
                                          self.MON))
        self.assertFalse(center_on_monitor((500, 500, 500, 500),
                                           self.MON))


if __name__ == "__main__":
    unittest.main()
