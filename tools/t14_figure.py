"""T14 figure + verdict numbers: A/B/C/D on identical recorded sessions.

A = refit only. B = click anchors (WebGazer-style, gated corrector).
C = Spark anchors via batch4-Huber (the discipline that actually fires).
D = SAM anchors via consensus corrector. Dots pooled by elapsed time.

Usage: .\\.venv\\Scripts\\python.exe tools\\t14_figure.py
Writes docs/fig_error_time.svg and prints the table for EVAL.md.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eval.report import write_figure  # noqa: E402
from eval.strategies import error_over_time, mean_error, run_strategy  # noqa: E402
from gaze.calibration import fit_calibration  # noqa: E402
from gaze.features import map_to_screen  # noqa: E402
from tools.replay_v2 import load, run_batch4, run_consensus  # noqa: E402

SESSIONS = ["data/sess-20261027-210940", "data/sess-20261030-084907"]


def clicks_of(spath):
    out = []
    with open(os.path.join(spath, "events.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            e = json.loads(line)
            if e["kind"] == "click":
                x, y = e["payload"]["pos"]
                out.append((e["t_mono"], float(x), float(y), 1.0, "click"))
    return out


def main():
    pooled = {"A": [], "B": [], "C": [], "D": []}
    for spath in SESSIONS:
        _m, calib, gaze, dots, anchors = load(spath)
        refit = fit_calibration(calib)
        k = len(calib[0][0])
        means = [sum(s[0][j] for s in calib) / len(calib) for j in range(k)]
        events = [{"t_mono": t, "kind": "gaze", "payload": {"features": f}}
                  for t, f in gaze]
        t0 = dots[0][0]
        series = {}
        series["A"] = error_over_time(
            [(t, map_to_screen(f, refit)) for t, f in gaze], dots, 1.0)
        feed_b = clicks_of(spath)
        preds_b, _log = run_strategy(events, dots, refit, feed_b)
        series["B"] = error_over_time(preds_b, dots, 1.0)
        feed_c = sorted(anchors.get("C", []), key=lambda a: a[0])
        preds_c, applied = run_batch4(events, refit, feed_c)
        series["C"] = error_over_time(preds_c, dots, 1.0)
        feed_d = sorted(anchors.get("D", []), key=lambda a: a[0])
        preds_d, _states = run_consensus(events, refit, means, feed_d)
        series["D"] = error_over_time(preds_d, dots, 1.0)
        print(f"{spath}: clicks={len(feed_b)} C={len(feed_c)} "
              f"(applied {applied}) D={len(feed_d)}")
        for name, s in series.items():
            late = [e for t, e in s if t - t0 >= 600]
            print(f"  {name}: mean={mean_error(s):.0f}px "
                  f"late(>=600s)={sum(late) / len(late):.0f}px")
            pooled[name] += [(t - t0, e) for t, e in s]
    for name in pooled:
        pooled[name].sort()
    out = os.path.join("docs", "fig_error_time.svg")
    write_figure(pooled, out)
    print(f"\nfigure: {out}")
    for name, s in pooled.items():
        late = [e for t, e in s if t >= 600]
        print(f"POOLED {name}: mean={mean_error(s):.0f}px "
              f"late={sum(late) / len(late):.0f}px n={len(s)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
