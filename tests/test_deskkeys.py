"""T29: desktop-demo key plumbing. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.deskkeys import bar_keys, grid_keys, label_to_tokens, place
from app.speak import build_command
from app.inject import key_events
from app.keyboard_layout import hit_key


class TestDeskKeys(unittest.TestCase):
    def test_place_offsets(self):
        keys = place([{"label": "A", "rect": (0, 0, 10, 10)}], 5, 7)
        self.assertEqual(keys[0]["rect"], (5, 7, 15, 17))
        self.assertEqual(hit_key(keys, 6, 8), "A")
        self.assertIsNone(hit_key(keys, 0, 0))

    def test_bar_even_split(self):
        keys = bar_keys(["a", "b", "c"], 0, 0, 330, 40, gap=15)
        self.assertEqual(len(keys), 3)
        self.assertEqual(hit_key(keys, 10, 10), "a")
        self.assertEqual(hit_key(keys, 320, 10), "c")

    def test_labels_to_tokens(self):
        self.assertEqual(label_to_tokens("SPACE", "hi"), (" ", "hi "))
        self.assertEqual(label_to_tokens("DELETE", "hi"), ("{BKSP}", "h"))
        self.assertEqual(label_to_tokens("ENTER", "hi"), ("{ENTER}", "hi"))
        self.assertEqual(label_to_tokens("WIN", ""), ("{WIN}", ""))
        self.assertEqual(label_to_tokens("ESC", ""), ("{ESC}", ""))
        self.assertEqual(label_to_tokens("H", ""), ("H", "H"))

    def test_suggestion_replaces_prefix(self):
        send, new = label_to_tokens("hola", "ho")
        self.assertEqual(new, "hola ")
        self.assertEqual(send, "{BKSP}{BKSP}hola ")
        send2, new2 = label_to_tokens("mundo", "hola ")
        self.assertEqual((send2, new2), ("mundo ", "hola mundo "))

    def test_esc_token_builds(self):
        evs = key_events("{ESC}")
        self.assertEqual(len(evs), 2)
        self.assertEqual(evs[0].u.ki.wVk, 0x1B)

    def test_grid_layout(self):
        keys = grid_keys(["A", "B", "C", "D"], 2, 2, 0, 0, 220, 220, gap=20)
        self.assertEqual(len(keys), 4)
        self.assertEqual(hit_key(keys, 10, 10), "A")
        self.assertEqual(hit_key(keys, 210, 210), "D")
        self.assertIsNone(hit_key(keys, 105, 105))

    def test_speak_command_quotes(self):
        cmd = build_command('hola "x"')
        self.assertIn("powershell", cmd[0].lower())
        self.assertIn("hola x", cmd[-1])
        self.assertNotIn('"x"', cmd[-1])

    def test_speak_command_voice_selects(self):
        cmd = build_command("hola", voice="Microsoft Sabina Desktop")
        self.assertIn("SelectVoice", cmd[-1])
        self.assertIn("Microsoft Sabina Desktop", cmd[-1])

    def test_speak_command_no_voice_default(self):
        self.assertNotIn("SelectVoice", build_command("hola")[-1])


if __name__ == "__main__":
    unittest.main()
