"""Does the factorial enrollment (A+B+E) beat A-only on held-out dots?

Sessions log calib captures in plan order: A = first 9 (natural 3x3),
B = next 25 (5 dots x 5 poses), E = last 9 (A repeated). Fit on A only
vs on A+B, score both on E (never fitted). Paired per session.

Usage: .\\.venv\\Scripts\\python.exe tools\\factorial_ablation.py
"""

import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gaze.calibration import fit_calibration  # noqa: E402
from gaze.features import map_to_screen  # noqa: E402


def calib_of(spath):
    out = []
    path = os.path.join(spath, "events.jsonl")
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e["kind"] == "calib":
                p = e["payload"]
                out.append((p["features"], p["target"][0], p["target"][1]))
    return out


def med_err(matrix, samples):
    errs = []
    for f, gx, gy in samples:
        px, py = map_to_screen(f, matrix)
        errs.append(((px - gx) ** 2 + (py - gy) ** 2) ** 0.5)
    return statistics.median(errs) if errs else float("nan")


def main():
    rows = []
    for spath in sorted(glob.glob("data/beta-*") + glob.glob("data/web-*")):
        s = calib_of(spath)
        if len(s) < 43:
            continue
        a, b, e = s[:9], s[9:34], s[34:43]
        try:
            err_a = med_err(fit_calibration(a), e)
            err_ab = med_err(fit_calibration(a + b), e)
        except Exception:
            continue
        rows.append((os.path.basename(spath), err_a, err_ab))
    print(f"{'session':<26} {'A-only':>8} {'A+B':>8} {'delta':>8}")
    for name, ea, eb in rows:
        print(f"{name:<26} {ea:>6.0f}px {eb:>6.0f}px {eb - ea:>+6.0f}px")
    if rows:
        ma = statistics.median(r[1] for r in rows)
        mb = statistics.median(r[2] for r in rows)
        wins = sum(1 for r in rows if r[2] < r[1])
        print(f"\nMedian held-out E error: A-only={ma:.0f}px A+B={mb:.0f}px "
              f"({(mb - ma) / ma * 100:+.0f}%), A+B wins {wins}/{len(rows)}")
    print("Factorial ablation done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
