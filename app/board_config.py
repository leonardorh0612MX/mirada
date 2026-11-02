"""Board settings persistence. Stdlib only, pure load/save.

data/board_config.json: {"voice_lang": "es"|"en", "phrases": {LABEL: text},
"apps": [{"label": ..., "launch": ...}]}. Unknown labels are ignored on
load; a missing/corrupt file yields defaults (including DEFAULT_APPS).
"""

import json
import os

DEFAULTS = {"voice_lang": "en", "phrases": {}}
DEFAULT_APPS = [
    {"label": "DISCORD", "launch": "discord"},
    {"label": "BROWSER", "launch": "https://www.google.com"},
    {"label": "YOUTUBE", "launch": "https://www.youtube.com"},
    {"label": "WHATSAPP", "launch": "https://web.whatsapp.com"},
    {"label": "MAIL", "launch": "https://mail.google.com"},
    {"label": "MAPS", "launch": "https://www.google.com/maps"},
]
DEFAULT_APPS_ES = [
    {"label": "DISCORD", "launch": "discord"},
    {"label": "NAVEGADOR", "launch": "https://www.google.com"},
    {"label": "YOUTUBE", "launch": "https://www.youtube.com"},
    {"label": "WHATSAPP", "launch": "https://web.whatsapp.com"},
    {"label": "CORREO", "launch": "https://mail.google.com"},
    {"label": "MAPAS", "launch": "https://www.google.com/maps"},
]


def default_apps(lang):
    """Fresh default app tiles for the language. Pure."""
    base = DEFAULT_APPS_ES if lang == "es" else DEFAULT_APPS
    return [dict(a) for a in base]


def valid_apps(raw):
    """Sanitize an apps list from JSON. Pure: [{label, launch}] only."""
    out = []
    if isinstance(raw, list):
        for item in raw[:8]:
            if not isinstance(item, dict):
                continue
            label, launch = item.get("label"), item.get("launch")
            if (isinstance(label, str) and label.strip()
                    and isinstance(launch, str) and launch.strip()):
                out.append({"label": label.strip().upper(),
                            "launch": launch.strip()})
    return out


def load_config(path, known_labels, lang="en"):
    cfg = {"voice_lang": DEFAULTS["voice_lang"], "phrases": {},
           "apps": default_apps(lang)}
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
        apps = valid_apps(raw.get("apps"))
        if apps:
            cfg["apps"] = apps
    return cfg


def save_config(path, voice_lang, phrases, apps=None):
    tmp = path + ".tmp"
    data = {"voice_lang": voice_lang, "phrases": phrases}
    if apps is not None:
        data["apps"] = apps
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
