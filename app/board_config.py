"""Board settings persistence. Stdlib only, pure load/save.

data/board_config.json: {"voice_lang": "es"|"en", "phrases": {LABEL: text}}.
Unknown labels are ignored on load; a missing/corrupt file yields defaults.
"""

import json
import os

DEFAULTS = {"voice_lang": "es", "phrases": {}}


def load_config(path, known_labels):
    cfg = {"voice_lang": DEFAULTS["voice_lang"], "phrases": {}}
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:
        return cfg
    if isinstance(raw, dict):
        if raw.get("voice_lang") in ("es", "en"):
            cfg["voice_lang"] = raw["voice_lang"]
        phrases = raw.get("phrases")
        if isinstance(phrases, dict):
            for label in known_labels:
                text = phrases.get(label)
                if isinstance(text, str) and text.strip():
                    cfg["phrases"][label] = text.strip()
    return cfg


def save_config(path, voice_lang, phrases):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"voice_lang": voice_lang, "phrases": phrases}, fh,
                  ensure_ascii=False, indent=1)
    os.replace(tmp, path)
