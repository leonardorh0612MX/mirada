"""App launching for the board APPS page (D16). Stdlib only.

The board's accuracy regime owns huge tiles, not 48 px taskbar icons, so
apps open from gaze-sized tiles. resolve_launch is pure (tested): it maps
a config launch string to an action without touching the OS. open_app
executes it and never raises.
"""

import os
import subprocess


def resolve_launch(launch, exists=None, local_app_data=None):
    """Launch string -> (kind, payload). Pure.

    ("url", url) for http(s) or scheme links, ("exe", [path, args...])
    for a found native app, ("shell", target) for anything else the OS
    shell should resolve (paths, .lnk, calc:, ...).
    """
    if exists is None:
        exists = os.path.exists
    if local_app_data is None:
        local_app_data = os.environ.get("LOCALAPPDATA", "")
    t = (launch or "").strip()
    low = t.lower()
    if low.startswith(("http://", "https://")):
        return ("url", t)
    if low == "discord":
        upd = os.path.join(local_app_data, "Discord", "Update.exe")
        if exists(upd):
            return ("exe", [upd, "--processStart", "Discord.exe"])
        return ("url", "https://discord.com/app")
    if "://" in t or low.endswith((".exe", ".lnk")) or os.sep in t:
        return ("shell", t)
    return ("shell", t)


def open_app(entry, exists=None, local_app_data=None):
    """Execute one {label, launch} entry. Returns (ok, detail)."""
    try:
        kind, payload = resolve_launch(entry.get("launch", ""), exists,
                                       local_app_data)
        if kind == "exe":
            subprocess.Popen(payload)
            return True, "exe"
        os.startfile(payload)  # Windows shell: urls, paths, schemes
        return True, kind
    except Exception as e:  # never take the board down for a bad target
        return False, f"{type(e).__name__}: {e}"
