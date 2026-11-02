"""Language tables: English default, 8 cells per lang, stable func ids.

The contest is judged in English: the default must be "en" and every
Spanish string must have an English twin (and vice versa), so no
session can show a half-translated UI. Stdlib only.
"""
import unittest

from app.i18n import (DEFAULT_LANG, LANGS, cells_for_lang, funcs_for_lang,
                      norm_lang, s)


class TestI18n(unittest.TestCase):
    def test_default_is_english(self):
        self.assertEqual(DEFAULT_LANG, "en")
        self.assertEqual(norm_lang("en"), "en")
        self.assertEqual(norm_lang("es"), "es")
        self.assertEqual(norm_lang("fr"), "en")
        self.assertEqual(norm_lang(None), "en")

    def test_cells_eight_per_lang_unique_labels(self):
        for lang in LANGS:
            cells = cells_for_lang(lang)
            self.assertEqual(len(cells), 8)
            labels = [c[0] for c in cells]
            self.assertEqual(len(set(labels)), 8)
            for _label, phrase in cells:
                self.assertTrue(phrase.strip())

    def test_cell_labels_differ_by_lang(self):
        en = [c[0] for c in cells_for_lang("en")]
        es = [c[0] for c in cells_for_lang("es")]
        self.assertNotEqual(en, es)

    def test_func_ids_stable_across_langs(self):
        for row in ("main", "apps", "kb"):
            ids_en = [f[0] for f in funcs_for_lang("en", row)]
            ids_es = [f[0] for f in funcs_for_lang("es", row)]
            self.assertEqual(ids_en, ids_es)
            self.assertIn("quit", ids_en)

    def test_string_parity_both_directions(self):
        from app.i18n import STR

        self.assertEqual(set(STR["en"]), set(STR["es"]))

    def test_lookup_falls_back_to_english(self):
        self.assertEqual(s("es", "tk_save"), "Guardar")
        self.assertEqual(s("fr", "tk_save"), "Save")
        self.assertEqual(s("en", "tk_calib", 3, 43), "CALIBRATION · 3/43")


if __name__ == "__main__":
    unittest.main()
