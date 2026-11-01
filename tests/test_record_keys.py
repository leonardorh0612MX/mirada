"""Shift+Q quit semantics with real pynput key objects."""

import importlib.util
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from pynput import keyboard

    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


def load_tool():
    spec = importlib.util.spec_from_file_location(
        "record_session", os.path.join(REPO, "tools", "record_session.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["record_session"] = mod
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(HAS_PYNPUT, "pynput not installed in this shell")
class TestQuitKeys(unittest.TestCase):
    def setUp(self):
        self.mod = load_tool()
        self.s = self.mod.new_key_state()
        self.K = keyboard.Key
        self.C = keyboard.KeyCode.from_char

    def test_plain_q_does_not_quit(self):
        self.mod.press_key(self.s, self.C("q"), keyboard)
        self.assertFalse(self.s["quit"])

    def test_uppercase_q_quits(self):
        self.mod.press_key(self.s, self.C("Q"), keyboard)
        self.assertTrue(self.s["quit"])

    def test_shift_then_q_quits(self):
        self.mod.press_key(self.s, self.K.shift, keyboard)
        self.mod.press_key(self.s, self.C("q"), keyboard)
        self.assertTrue(self.s["quit"])

    def test_shift_released_then_q_does_not_quit(self):
        self.mod.press_key(self.s, self.K.shift, keyboard)
        self.mod.release_key(self.s, self.K.shift, keyboard)
        self.mod.press_key(self.s, self.C("q"), keyboard)
        self.assertFalse(self.s["quit"])

    def test_space_confirms(self):
        self.mod.press_key(self.s, self.K.space, keyboard)
        self.assertTrue(self.s["space"])
        self.assertFalse(self.s["quit"])

    def test_other_keys_ignored(self):
        self.mod.press_key(self.s, self.C("a"), keyboard)
        self.assertEqual(self.s, {"space": False, "quit": False, "shift": False})


class TestFixationBuffer(unittest.TestCase):
    def setUp(self):
        self.mod = load_tool()

    def test_not_ready_below_min(self):
        fb = self.mod.FixationBuffer(min_frames=10)
        for _ in range(5):
            fb.add([1.0, 2.0])
        self.assertFalse(fb.ready())
        self.assertIsNone(fb.average())

    def test_none_frames_ignored(self):
        fb = self.mod.FixationBuffer(min_frames=3)
        fb.add(None)
        fb.add([0.0, 0.0])
        fb.add([0.01, 0.0])
        self.assertFalse(fb.ready())
        fb.add([0.0, 0.01])
        self.assertTrue(fb.ready())

    def test_unstable_window_not_ready(self):
        fb = self.mod.FixationBuffer(min_frames=4)
        for v in (0.0, 0.0, 0.5, 0.5):
            fb.add([v, 0.0])
        self.assertFalse(fb.ready())

    def test_single_spike_tolerated(self):
        fb = self.mod.FixationBuffer(min_frames=6)
        for v in (0.0, 0.0, 0.0, 0.09, 0.0, 0.0):
            fb.add([v, 0.0])
        self.assertTrue(fb.ready())

    def test_average_tail(self):
        fb = self.mod.FixationBuffer(min_frames=10, tail_n=40)
        for i in range(50):
            fb.add([10.0 + 0.001 * (i % 2), 1.0])
        avg = fb.average()
        self.assertAlmostEqual(avg[0], 10.0005, places=3)
        self.assertAlmostEqual(avg[1], 1.0)


if __name__ == "__main__":
    unittest.main()
