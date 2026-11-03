"""resolve_camera routing: flag wins, probe decides the rest."""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.camselect import resolve_camera, resolve_monitor, sync_probe_caps


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


class TestSyncProbeCaps(unittest.TestCase):
    def test_hotplug_adds_only_new_indices(self):
        import threading

        live = {0: (FakeCap(), threading.Lock(),
                    {"t": 0.0, "jpg": None, "fail": 0})}
        opened = []

        def opener(i):
            opened.append(i)
            return FakeCap() if i == 2 else None

        self.assertEqual(sync_probe_caps(live, opener, n=3), [0, 2])
        self.assertNotIn(1, live)
        self.assertEqual(live[2][2]["fail"], 0)
        # Already-open index is never re-opened (DSHOW is slow).
        self.assertNotIn(0, opened)

    def test_quarantined_indices_are_skipped(self):
        live = {}
        opened = []

        def opener(i):
            opened.append(i)
            return FakeCap()

        self.assertEqual(sync_probe_caps(live, opener, n=3, skip={1}), [0, 2])
        self.assertNotIn(1, opened)


if __name__ == "__main__":
    unittest.main()
