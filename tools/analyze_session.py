"""Analyze one recorded session: event counts + strategy A dot errors.

Usage: .\\.venv\\Scripts\\python.exe tools\\analyze_session.py data\\sess-XXXX
Stdlib only. Runs anywhere.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.replay import error_over_time, replay_a, summarize


def main():
    if len(sys.argv) < 2:
        print("usage: analyze_session.py <session_dir>")
        return 2
    spath = sys.argv[1]
    matrix = None
    events, dots, calib = [], [], []
    kinds = {}
    with open(os.path.join(spath, "events.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
            if e["kind"] == "calibration_matrix":
                matrix = e["payload"]["matrix"]
            elif e["kind"] == "gaze":
                events.append({"t_mono": e["t_mono"], "kind": "gaze",
                               "payload": {"features": e["payload"]["features"]}})
            elif e["kind"] == "dot":
                dots.append((e["t_mono"], tuple(e["payload"]["pos"]),
                             e["payload"].get("features_avg")))
            elif e["kind"] == "calib":
                calib.append(e)
    print(f"events by kind: {kinds}")
    print(f"calib samples: {len(calib)} dots: {len(dots)} matrix: {matrix is not None}")
    if matrix is None or not dots:
        print("no matrix or no dots: cannot score.")
        return 0
    from gaze.features import map_to_screen

    preds = replay_a(events, matrix)
    series = []
    for t_dot, pos, favg in dots:
        if favg is not None:
            pred = map_to_screen(favg, matrix)
        else:
            near = [p for t, p in preds if abs(t - t_dot) <= 1.0]
            if near:
                pred = (sum(p[0] for p in near) / len(near),
                        sum(p[1] for p in near) / len(near))
            else:
                best = min(preds, key=lambda p: abs(p[0] - t_dot), default=None)
                if best is None:
                    continue
                pred = best[1]
        err = ((pred[0] - pos[0]) ** 2 + (pred[1] - pos[1]) ** 2) ** 0.5
        series.append((t_dot, err))
    for t, err in series:
        print(f"dot t={t:.0f}s error={err:.1f}px")
    s = summarize(series)
    print(f"strategy A: n={s['n']} mean={s['mean_px']:.1f}px")
    span = events[-1]["t_mono"] - events[0]["t_mono"] if events else 0
    print(f"session span: {span:.0f}s gaze events: {len(events)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
