"""Offline speech via Windows System.Speech. Stdlib only.

A single daemon worker speaks utterances in order without blocking the
gaze loop (a PowerShell plus a 3 s phrase would freeze tracking).
Voices are picked by culture prefix (es-/en-), never by hardcoded name:
list_voices queries once, lazily, inside the worker. build_command,
parse_voices and pick_voices are pure and tested; speak touches the OS
and is covered live.
"""

import queue
import subprocess
import threading
import time

_WORKER = {"queue": None, "thread": None, "lock": threading.Lock()}
_LANG = {"lang": "es"}
_VOICES = {"done": False, "es": None, "en": None, "tried_at": -100.0}


def build_command(text, voice=None):
    safe = text.replace('"', "")
    synth = "(New-Object System.Speech.Synthesis.SpeechSynthesizer)"
    sel = f"$s={synth}; $s.SelectVoice(\"{voice}\".replace('\"', '')); " if voice else ""
    verb = "$s.Speak" if voice else f"{synth}.Speak"
    script = ("Add-Type -AssemblyName System.Speech; " + sel +
              f'{verb}("{safe}")')
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def parse_voices(output):
    """'culture | name' lines -> [(culture, name)]. Pure."""
    out = []
    for line in output.splitlines():
        if "|" not in line:
            continue
        culture, name = (part.strip() for part in line.split("|", 1))
        if culture and name:
            out.append((culture, name))
    return out


def pick_voices(pairs):
    """First es-* and en-* voice names. Pure. Missing -> None (default)."""
    pick = {"es": None, "en": None}
    for culture, name in pairs:
        for lang in ("es", "en"):
            if pick[lang] is None and culture.lower().startswith(lang):
                pick[lang] = name
    return pick


def list_voices():
    """Query installed voices. Never raises; [] on any failure."""
    try:
        script = ("Add-Type -AssemblyName System.Speech; "
                  "(New-Object System.Speech.Synthesis.SpeechSynthesizer)"
                  ".GetInstalledVoices() | ForEach-Object { "
                  "$_.VoiceInfo.Culture.Name + ' | ' + $_.VoiceInfo.Name }")
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                            "-Command", script], timeout=20, capture_output=True,
                           text=True, check=False)
        return parse_voices(r.stdout or "")
    except Exception:
        return []


def set_language(lang):
    """'es' or 'en'. Unknown values keep the current language."""
    if lang in ("es", "en"):
        _LANG["lang"] = lang


def current_voice():
    """Resolved voice name for the current language, None = default.

    A failed/empty query is never cached: it retries after 10 s. Caching
    an empty result once left a whole session on the American default
    while the config said Spanish (web-20261031-225501).
    """
    now = time.monotonic()
    if not _VOICES["done"] and now - _VOICES["tried_at"] > 10.0:
        _VOICES["tried_at"] = now
        found = pick_voices(list_voices())
        _VOICES.update(found)
        _VOICES["done"] = bool(found["es"] or found["en"])
    return _VOICES.get(_LANG["lang"])


def voice_status():
    """{'lang', 'es', 'en', 'active'} for startup logs. Never raises."""
    try:
        current_voice()
    except Exception:
        pass
    return {"lang": _LANG["lang"], "es": _VOICES.get("es"),
            "en": _VOICES.get("en"), "active": _VOICES.get(_LANG["lang"])}


def _worker(q):
    while True:
        text = q.get()
        if text is None:
            return
        try:
            subprocess.run(build_command(text, current_voice()), timeout=20,
                           capture_output=True, check=False)
        except Exception:
            pass
        q.task_done()


def speak(text):
    """Queue one utterance; returns immediately, never raises."""
    try:
        with _WORKER["lock"]:
            if _WORKER["queue"] is None:
                _WORKER["queue"] = queue.Queue()
                _WORKER["thread"] = threading.Thread(
                    target=_worker, args=(_WORKER["queue"],), daemon=True)
                _WORKER["thread"].start()
            _WORKER["queue"].put(text)
    except Exception:
        pass
