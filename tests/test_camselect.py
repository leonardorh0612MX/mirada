"""resolve_camera routing: flag wins, probe decides the rest."""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.camselect import resolve_camera, resolve_monitor


class FakeCap:
    def release(self):
        pass


def quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class TestResolveCamera(unittest.TestCase):
    def test_explicit_flag_wins_without_probing(self):
        def boom():
            raise AssertionError("must not probe")

        self.assertEqual(resolve_camera(2, probe=boom), 2)

    def test_single_camera_used_silently(self):
        self.assertEqual(quiet(resolve_camera, None, probe=lambda: [(1, FakeCap())]), 1)

    def test_no_camera_returns_none(self):
        self.assertIsNone(quiet(resolve_camera, None, probe=lambda: []))


class TestResolveMonitor(unittest.TestCase):
    def test_explicit_flag_wins_without_probing(self):
        def boom():
            raise AssertionError("must not probe")

        self.assertEqual(resolve_monitor(1, probe=boom), 1)

    def test_single_monitor_used_silently(self):
        found = [(0, (0, 0, 1920, 1080), None)]
        self.assertEqual(quiet(resolve_monitor, None, probe=lambda: found), 0)

    def test_no_monitor_returns_none(self):
        self.assertIsNone(quiet(resolve_monitor, None, probe=lambda: []))


if __name__ == "__main__":
    unittest.main()
