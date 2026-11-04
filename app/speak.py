"""Offline speech via Windows System.Speech. Stdlib only.

A single daemon worker speaks utterances in order without blocking the
gaze loop (a PowerShell plus a 3 s phrase would freeze tracking).
Voices are picked by culture prefix (es-/en-), never by hardcoded name:
list_voices queries once, lazily, inside the worker. Speech runs
through ONE persistent PowerShell (a fresh process per utterance cost
~1 s of dead air before every calibration instruction); any shell
failure falls back to the old one-shot command. build_command,
parse_voices, pick_voices and clean_utterance are pure and tested;
speak touches the OS and is covered live.
"""

import queue
import subprocess
import threading
import time

_WORKER = {"queue": None, "thread": None, "lock": threading.Lock()}
_LANG = {"lang": "es"}
_VOICES = {"done": False, "es": None, "en": None, "tried_at": -100.0}
_SHELL = {"proc": None, "lock": threading.Lock(), "dead": False,
          "fails": 0, "lines": queue.Queue()}

_SHELL_BOOT = (
    "[Console]::InputEncoding = [System.Text.Encoding]::UTF8; "
    "Add-Type -AssemblyName System.Speech; "
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    "$v = ''; "
    "while (($voice = [Console]::In.ReadLine()) -ne $null) { "
    "  $text = [Console]::In.ReadLine(); "
    "  if ($text -eq $null) { break } "
    "  if ($voice -ne $v) { $v = $voice; "
    "    if ($v -ne '') { $s.SelectVoice($v) } } "
    "  try { $s.Speak($text) } catch { } "
    "  [Console]::Out.WriteLine('DONE'); [Console]::Out.Flush() "
    "}"
)


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


def clean_utterance(text):
    """Shell-protocol-safe text: one line, no quotes. Pure."""
    return " ".join(str(text).replace('"', "").split())


def _shell_start():
    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive",
         "-Command", _SHELL_BOOT],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
        errors="replace", bufsize=1)

    def _reader():
        try:
            while True:
                line = proc.stdout.readline()
                _SHELL["lines"].put(line.strip() if line else None)
                if not line:
                    return
        except Exception:
            _SHELL["lines"].put(None)

    threading.Thread(target=_reader, daemon=True).start()
    return proc


def _shell_alive(proc):
    return proc is not None and proc.poll() is None


def _say_shell(text, voice):
    """Speak via the persistent shell. True on DONE, False to fallback."""
    with _SHELL["lock"]:
        if _SHELL["dead"]:
            return False
        try:
            if not _shell_alive(_SHELL["proc"]):
                _SHELL["proc"] = _shell_start()
            while True:  # drop stale death markers from a prior proc
                try:
                    _SHELL["lines"].get_nowait()
                except queue.Empty:
                    break
            _SHELL["proc"].stdin.write(f"{voice or ''}\n{text}\n")
            _SHELL["proc"].stdin.flush()
        except Exception:
            _note_shell_failure()
            return False
    try:
        ok = _SHELL["lines"].get(timeout=8.0 + len(text) * 0.3)
    except queue.Empty:
        ok = None
    if ok != "DONE":
        with _SHELL["lock"]:
            _note_shell_failure()
        return False
    return True


def _note_shell_failure():
    try:
        if _SHELL["proc"] is not None:
            _SHELL["proc"].kill()
    except Exception:
        pass
    _SHELL["proc"] = None
    _SHELL["fails"] += 1
    if _SHELL["fails"] >= 2:
        _SHELL["dead"] = True  # stop paying restarts; one-shot works


def _say_one(text, voice):
    text = clean_utterance(text)
    if not text:
        return
    if _say_shell(text, voice or ""):
        return
    try:
        subprocess.run(build_command(text, voice), timeout=20,
                       capture_output=True, check=False)
    except Exception:
        pass


def prewarm():
    """Start the voice shell early (fire-and-forget thread).

    Called once the session language is known so the first spoken
    instruction doesn't pay process + synthesizer startup (~2 s).
    """
    def _go():
        try:
            current_voice()
            with _SHELL["lock"]:
                if not _SHELL["dead"] and not _shell_alive(_SHELL["proc"]):
                    _SHELL["proc"] = _shell_start()
        except Exception:
            pass

    threading.Thread(target=_go, daemon=True).start()


def _worker(q):
    while True:
        item = q.get()
        if item is None:
            return
        text, done = item if isinstance(item, tuple) else (item, None)
        try:
            _say_one(text, current_voice())
        except Exception:
            pass
        finally:
            if done is not None:
                done.set()
        q.task_done()


def _ensure_worker():
    with _WORKER["lock"]:
        if _WORKER["queue"] is None:
            _WORKER["queue"] = queue.Queue()
            _WORKER["thread"] = threading.Thread(
                target=_worker, args=(_WORKER["queue"],), daemon=True)
            _WORKER["thread"].start()
        return _WORKER["queue"]


def speak(text):
    """Queue one utterance; returns immediately, never raises."""
    try:
        _ensure_worker().put(text)
    except Exception:
        pass


def speak_sync(text, timeout=12.0):
    """Speak one utterance, wait until it finishes. True if done.

    For calibration instructions: the user fixates the dot and cannot
    read the footer, so capture starts only after the voice ends.
    Never raises; False on timeout (capture proceeds anyway - a stuck
    voice must never hang enrollment).
    """
    try:
        done = threading.Event()
        _ensure_worker().put((text, done))
        return done.wait(timeout)
    except Exception:
        return False
