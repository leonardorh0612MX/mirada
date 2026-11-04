"""resolve_camera routing: flag wins, probe decides the rest."""

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.camselect import (prune_dead_caps, resolve_camera, resolve_monitor,
                             sync_probe_caps)


class FakeCap:
    def release(self):
        pass


class ScriptCap:
    """read() follows a script of ok/None outcomes, then repeats the last."""

    def __init__(self, script):
        self.script = list(script)
        self.reads = 0
        self.released = False

    def read(self):
        self.reads += 1
        ok = self.script[min(self.reads - 1, len(self.script) - 1)]
        return (True, object()) if ok else (False, None)

    def release(self):
        self.released = True


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
                    {"t": 0.0, "jpg": None})}
        opened = []

        def opener(i):
            opened.append(i)
            return FakeCap() if i == 2 else None

        self.assertEqual(sync_probe_caps(live, opener, n=3), [0, 2])
        self.assertNotIn(1, live)
        self.assertEqual(live[2][2], {"t": 0.0, "jpg": None})
        # Already-open index is never re-opened (DSHOW is slow).
        self.assertNotIn(0, opened)

    def test_skipped_indices_are_ignored(self):
        live = {}
        opened = []

        def opener(i):
            opened.append(i)
            return FakeCap()

        self.assertEqual(sync_probe_caps(live, opener, n=3, skip={1}), [0, 2])
        self.assertNotIn(1, opened)


class TestPruneDeadCaps(unittest.TestCase):
    def _entry(self, cap):
        import threading

        return (cap, threading.Lock(), {"t": 0.0, "jpg": None})

    def test_stuttering_camera_is_kept(self):
        # Regression (Nov 3): the old auto-drop ate a working Logitech
        # on transient DSHOW failures. Two bad reads then a good one
        # must keep the card.
        cap = ScriptCap([False, False, True])
        live = {0: self._entry(cap)}
        self.assertEqual(prune_dead_caps(live), [])
        self.assertIn(0, live)
        self.assertFalse(cap.released)

    def test_dead_camera_is_dropped_and_released(self):
        cap = ScriptCap([False])
        live = {0: self._entry(cap)}
        self.assertEqual(prune_dead_caps(live, tries=3), [0])
        self.assertNotIn(0, live)
        self.assertTrue(cap.released)
        self.assertEqual(cap.reads, 3)

    def test_healthy_camera_costs_one_read(self):
        cap = ScriptCap([True])
        live = {0: self._entry(cap)}
        self.assertEqual(prune_dead_caps(live), [])
        self.assertEqual(cap.reads, 1)

    def test_mixed_bag_prunes_only_the_dead(self):
        good, bad = ScriptCap([True]), ScriptCap([False])
        live = {0: self._entry(good), 2: self._entry(bad)}
        self.assertEqual(prune_dead_caps(live, tries=2), [2])
        self.assertIn(0, live)
        self.assertTrue(bad.released)
        self.assertFalse(good.released)


if __name__ == "__main__":
    unittest.main()
