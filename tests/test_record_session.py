"""Regression: record_session v2 helpers (floating dot overlay)."""

import importlib.util
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_tool():
    spec = importlib.util.spec_from_file_location(
        "record_session", os.path.join(REPO, "tools", "record_session.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["record_session"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestRecordSession(unittest.TestCase):
    def test_grid_points_cover_monitor(self):
        mod = load_tool()
        pts = mod.grid_points((1920, 0, 2560, 1440))
        self.assertEqual(len(pts), 9)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.assertAlmostEqual(min(xs), 1920 + 256)
        self.assertAlmostEqual(max(xs), 1920 + 2304)
        self.assertAlmostEqual(min(ys), 144)
        self.assertAlmostEqual(max(ys), 1296)

    def test_dot_schedule_spacing(self):
        from app.calibration import dot_schedule

        self.assertEqual(dot_schedule(600.0), [120.0, 240.0, 360.0, 480.0])

    @unittest.skipUnless(sys.platform == "win32", "Windows monitor enumeration")
    def test_list_monitors_shape(self):
        mod = load_tool()
        monitors = mod.list_monitors()
        self.assertGreaterEqual(len(monitors), 1)
        for left, top, w, h in monitors:
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)


if __name__ == "__main__":
    unittest.main()
