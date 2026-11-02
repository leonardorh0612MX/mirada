"""T27: population residual field, leave-one-session-out.

For every study session: fit the session's own base map on its stored
calibration, take the residual at each ground-truth dot (1 s median
features before the dot), then ask whether a Gaussian-basis field
trained on the OTHER sessions' residuals predicts this session's
residuals. Corrected error < base error on unseen sessions is the claim.

Usage: .\\.venv\\Scripts\\python.exe tools\\t27_residual.py
"""

import glob
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from gaze.calibration import fit_calibration  # noqa: E402
from gaze.features import map_to_screen  # noqa: E402
from gaze.residual import fit_residual, predict_residual  # noqa: E402
from tools.replay_v2 import load  # noqa: E402


def dot_samples(spath):
    """(feats_median, residual_xy, base_err) per ground-truth dot."""
    _matrix, calib, gaze, dots, _anchors = load(spath)
    if len(calib) < 8 or len(dots) < 4:
        return []
    refit = fit_calibration(calib)
    out = []
    for t, (dx, dy) in dots:
        # Recorder logs the dot at appearance; the fixation samples live
        # in the following second (same convention as error_over_time).
        win = [f for tg, f in gaze if abs(tg - t) <= 1.0]
        if len(win) < 5:
            continue
        med = [statistics.median(f[j] for f in win) for j in range(len(win[0]))]
        px, py = map_to_screen(med, refit)
        out.append((med, (dx - px, dy - py),
                    float(np.hypot(dx - px, dy - py))))
    return out


def main():
    sessions = {}
    for spath in sorted(glob.glob("data/sess-*")):
        samples = dot_samples(spath)
        if len(samples) >= 4:
            sessions[os.path.basename(spath)] = samples
    print(f"sessions with dot residuals: {len(sessions)}")
    rows, pooled_base, pooled_corr = [], [], []
    for name, test in sessions.items():
        dim = len(test[0][0])
        # Early sessions recorded 4 features, later ones 7: the field
        # only trains/tests within one feature dimension.
        train = [s for n, ss in sessions.items()
                 if n != name and len(ss[0][0]) == dim for s in ss]
        if len(train) < 10:
            print(f"{name}: skipped (dim={dim}, train={len(train)})")
            continue
        X = np.array([s[0] for s in train])
        Y = np.array([s[1] for s in train])
        model = fit_residual(X, Y, lam=1.0)
        base = [s[2] for s in test]
        corr = []
        for feats, (rx, ry), _e in test:
            prx, pry = predict_residual(model, [feats])[0]
            corr.append(float(np.hypot(rx - prx, ry - pry)))
        rows.append((name, len(test), np.mean(base), np.mean(corr)))
        pooled_base += base
        pooled_corr += corr
    print(f"\n{'session':<24} {'dots':>4} {'base':>7} {'+resid':>7} {'delta':>7}")
    for name, n, b, c in rows:
        print(f"{name:<24} {n:>4} {b:>6.0f}px {c:>6.0f}px {c - b:>+6.0f}px")
    if pooled_base:
        b, c = np.mean(pooled_base), np.mean(pooled_corr)
        wins = sum(1 for _n, _k, bb, cc in rows if cc < bb)
        print(f"\nPooled LOSO: base={b:.0f}px corrected={c:.0f}px "
              f"({(c - b) / b * 100:+.0f}%), sessions improved "
              f"{wins}/{len(rows)}, n={len(pooled_base)} dots")
    print("T27 done. Adopt only if LOSO clearly wins.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
