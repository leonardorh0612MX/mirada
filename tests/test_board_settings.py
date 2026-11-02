"""Voice picking (culture prefix, never hardcoded names) and config roundtrip."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.speak as speak_mod
from app.board_config import load_config, save_config
from app.speak import parse_voices, pick_voices

LABELS = ["SI", "NO"]


class TestVoices(unittest.TestCase):
    def test_parse_skips_junk_lines(self):
        out = parse_voices("es-MX | Microsoft Sabina Desktop\njunk\n| noname\n")
        self.assertEqual(out, [("es-MX", "Microsoft Sabina Desktop")])

    def test_pick_first_of_each_culture(self):
        pairs = [("en-US", "David"), ("es-MX", "Sabina"), ("es-ES", "Helena")]
        self.assertEqual(pick_voices(pairs), {"es": "Sabina", "en": "David"})

    def test_pick_missing_is_none(self):
        self.assertEqual(pick_voices([("fr-FR", "Hortense")]),
                         {"es": None, "en": None})


class TestVoiceRetry(unittest.TestCase):
    def tearDown(self):
        speak_mod._VOICES.update(done=False, es=None, en=None, tried_at=-100.0)
        speak_mod.set_language("es")

    def test_failed_query_not_cached(self):
        orig = speak_mod.list_voices
        try:
            speak_mod.list_voices = lambda: []
            self.assertIsNone(speak_mod.current_voice())
            speak_mod.list_voices = lambda: [("es-MX", "Sabina"),
                                             ("en-US", "Zira")]
            speak_mod._VOICES["tried_at"] = -100.0  # backoff elapsed
            self.assertEqual(speak_mod.current_voice(), "Sabina")
        finally:
            speak_mod.list_voices = orig

    def test_language_switch_changes_active_voice(self):
        orig = speak_mod.list_voices
        try:
            speak_mod.list_voices = lambda: [("es-MX", "Sabina"),
                                             ("en-US", "Zira")]
            speak_mod.set_language("es")
            self.assertEqual(speak_mod.current_voice(), "Sabina")
            speak_mod.set_language("en")
            self.assertEqual(speak_mod.current_voice(), "Zira")
            speak_mod.set_language("fr")  # unknown keeps current
            self.assertEqual(speak_mod.current_voice(), "Zira")
        finally:
            speak_mod.list_voices = orig

    def test_success_is_cached(self):
        orig = speak_mod.list_voices
        calls = []

        def fake():
            calls.append(1)
            return [("es-MX", "Sabina")]

        try:
            speak_mod.list_voices = fake
            speak_mod.current_voice()
            speak_mod.current_voice()
            self.assertEqual(len(calls), 1)
        finally:
            speak_mod.list_voices = orig


class TestBoardConfig(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cfg.json")
            save_config(p, "en", {"SI": "Yes please"})
            cfg = load_config(p, LABELS)
            self.assertEqual(cfg["voice_lang"], "en")
            self.assertEqual(cfg["phrases"], {"SI": "Yes please"})

    def test_missing_file_defaults(self):
        cfg = load_config(os.path.join("nope", "missing.json"), LABELS)
        self.assertEqual(cfg["voice_lang"], "en")
        self.assertEqual(cfg["phrases"], {})
        self.assertEqual([a["label"] for a in cfg["apps"]],
                         ["DISCORD", "BROWSER", "YOUTUBE", "WHATSAPP",
                          "MAIL", "MAPS"])

    def test_missing_file_spanish_apps(self):
        cfg = load_config(os.path.join("nope", "missing.json"), LABELS,
                          "es")
        self.assertEqual(cfg["voice_lang"], "en")
        self.assertEqual([a["label"] for a in cfg["apps"]],
                         ["DISCORD", "NAVEGADOR", "YOUTUBE", "WHATSAPP",
                          "CORREO", "MAPAS"])

    def test_apps_roundtrip_and_sanitize(self):
        from app.board_config import valid_apps

        self.assertEqual(valid_apps([{"label": " x ", "launch": " y "},
                                     {"label": 3, "launch": "z"}, "junk"]),
                         [{"label": "X", "launch": "y"}])
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cfg.json")
            apps = [{"label": "DISCORD", "launch": "discord"}]
            save_config(p, "es", {}, apps)
            self.assertEqual(load_config(p, LABELS)["apps"], apps)

    def test_unknown_labels_and_blank_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cfg.json")
            save_config(p, "es", {"SI": "  ", "XX": "nope", "NO": "No"})
            cfg = load_config(p, LABELS)
            self.assertEqual(cfg["phrases"], {"NO": "No"})

    def test_bad_lang_keeps_default(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cfg.json")
            save_config(p, "fr", {})
            cfg = load_config(p, LABELS)
            self.assertEqual(cfg["voice_lang"], "en")


class TestWebState(unittest.TestCase):
    def test_state_carries_voice_lang_for_modal(self):
        # The settings modal must read the language from server state,
        # never guess it client-side (web-225501: es config, en voice).
        import app.board_web as web

        self.assertIn(web.STATE["voice_lang"], ("es", "en"))
        self.assertIn("phrases", web.STATE)


if __name__ == "__main__":
    unittest.main()
