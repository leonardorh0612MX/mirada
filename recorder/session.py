"""Append-only session recording with monotonic ordering. Stdlib only.

One session is one directory: manifest.json plus events.jsonl, one JSON
object per line. Every event carries t_mono (seconds, monotonic clock) and
kind. Readers assert non-decreasing t_mono so replay order is trustworthy.
"""

import json
import os
import threading
import time

MANIFEST_NAME = "manifest.json"
EVENTS_NAME = "events.jsonl"
_WRITE_LOCK = threading.Lock()


def new_session(data_dir, name, meta=None):
    """Create a session directory. Returns its path."""
    path = os.path.join(data_dir, name)
    os.makedirs(path, exist_ok=False)
    manifest = {
        "name": name,
        "t_mono_start": time.monotonic(),
        "meta": meta or {},
    }
    with open(os.path.join(path, MANIFEST_NAME), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)
    open(os.path.join(path, EVENTS_NAME), "a", encoding="utf-8").close()
    return path


def append_event(session_path, kind, payload=None, t_mono=None):
    """Append one event. Returns the stored record.

    Thread-safe: record build and write happen under one lock. Without
    it, a click-listener thread's small write interleaved inside the
    capture loop's multi-KB landmark line and destroyed one record
    (sess-20261101-130237, line 78 of 8536).
    """
    with _WRITE_LOCK:
        record = {
            "t_mono": time.monotonic() if t_mono is None else t_mono,
            "kind": kind,
            "payload": payload or {},
        }
        path = os.path.join(session_path, EVENTS_NAME)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    return record


def read_events(session_path):
    """Read all events, asserting monotonic order."""
    events = []
    with open(os.path.join(session_path, EVENTS_NAME), encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if events and record["t_mono"] < events[-1]["t_mono"]:
                raise ValueError(f"t_mono went backwards at line {line_no}")
            events.append(record)
    return events
