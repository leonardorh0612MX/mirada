"""T29: Spanish word completion. Stdlib only."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.inject import key_events
from app.words import apply_suggestion, current_prefix, suggest

WORDS = ["hola", "holgazan", "hoja", "adios", "hombre", "hora"]


class TestWords(unittest.TestCase):
    def test_prefix(self):
        self.assertEqual(current_prefix("hola mun"), "mun")
        self.assertEqual(current_prefix("hola "), "")
        self.assertEqual(current_prefix(""), "")

    def test_suggest_frequency_order(self):
        self.assertEqual(suggest("ho", WORDS, k=3), ["hola", "holgazan", "hoja"])
        self.assertEqual(suggest("hol", WORDS), ["hola", "holgazan"])
        self.assertEqual(suggest("z", WORDS), [])
        self.assertEqual(suggest("", WORDS), [])

    def test_apply(self):
        self.assertEqual(apply_suggestion("ho", "hola"), "hola ")
        self.assertEqual(apply_suggestion("si ho", "hola"), "si hola ")
        self.assertEqual(apply_suggestion("hola ", "mundo"), "hola mundo ")


class TestKeyEvents(unittest.TestCase):
    def test_text_pair_per_char(self):
        self.assertEqual(len(key_events("ab")), 4)

    def test_special_tokens(self):
        evs = key_events("{ENTER}{BKSP}{WIN}")
        self.assertEqual(len(evs), 6)
        self.assertEqual(evs[0].u.ki.wVk, 0x0D)

    def test_unicode_accent(self):
        evs = key_events("ñ")
        self.assertEqual(evs[0].u.ki.wScan, ord("ñ"))


if __name__ == "__main__":
    unittest.main()
