"""Replay A/C/D on a recorded session with offline anchors. Stdlib only.

Usage: .\\.venv\\Scripts\\python.exe tools\\replay_offline.py data\\sess-XXXX
Needs anchors_offline.json (see tools/gen_anchors.py). B needs click events
and runs only when the session has them.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.replay import error_over_time as eot_a, replay_a, summarize
from eval.report import write_report
from eval.strategies import error_over_time, mean_error, run_strategy


def main():
    if len(sys.argv) < 2:
        print("usage: replay_offline.py <session_dir>")
        return 2
    spath = sys.argv[1]
    matrix, events, dots = None, [], []
    clicks = []
    with open(os.path.join(spath, "events.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e["kind"] == "calibration_matrix":
                matrix = e["payload"]["matrix"]
            elif e["kind"] == "gaze":
                events.append({"t_mono": e["t_mono"], "kind": "gaze",
                               "payload": {"features": e["payload"]["features"]}})
            elif e["kind"] == "dot":
                dots.append((e["t_mono"], tuple(e["payload"]["pos"])))
            elif e["kind"] == "click":
                clicks.append((e["t_mono"], *e["payload"]["pos"], 1.0, "click"))
    with open(os.path.join(spath, "anchors_offline.json"), encoding="utf-8") as fh:
        anchors = json.load(fh)

    series = {"A": eot_a(replay_a(events, matrix), dots, window_s=1.0)}
    feeds = {}
    if isinstance(anchors, dict):
        feeds = anchors
    else:  # legacy flat list counts as C
        feeds = {"C": anchors}
    for name, feed in feeds.items():
        preds, log = run_strategy(events, dots, matrix,
                                  [(a[0], a[1], a[2], a[3], a[4]) for a in feed])
        series[name] = error_over_time(preds, dots, window_s=1.0)
        acc = sum(1 for _, ok, _ in log if ok)
        print(f"{name}: {len(feed)} anchors, {acc} accepted, "
              f"{len(log) - acc} rejected")
    if clicks:
        preds, _ = run_strategy(events, dots, matrix, clicks)
        series["B"] = error_over_time(preds, dots)
        print(f"B: {len(clicks)} clicks")
    else:
        print("B: no click events in this session (skipped)")

    for t_dot, pos in dots:
        row = []
        for name in sorted(series):
            err = next((e for t, e in series[name] if t == t_dot), None)
            row.append(f"{name}={err:.0f}" if err is not None else f"{name}=-")
        print(f"dot t={t_dot:.0f} " + " ".join(row))
    print()
    out = write_report(series, os.path.join(spath, "report"))
    for name in sorted(out["summary"]):
        s = out["summary"][name]
        print(f"{name}: n={s['n']} mean={s['mean_px']:.0f}px slope={s['slope_px_s']:.4f}px/s")
    print(f"figure: {out['figure']} table: {out['table']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
