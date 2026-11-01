"""T20: appearance model (eye crops) vs linear feature map, offline A/B.

Dataset: crops saved every 12th gaze event (filename = gaze sequence
number). Labeled pairs = crops within +-1s of a ground-truth dot.
Baseline: linear 7-feature fit on the session's calib samples.
Challenger: ridge on downsampled L+R grayscale crops (24x16 each).
Protocol: leave-one-dot-out CV per session. Adopt only on a clear win.

Usage: .\\.venv\\Scripts\\python.exe tools\\t20_appearance.py
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

from gaze.calibration import fit_calibration
from gaze.features import map_to_screen


def load_session(spath):
    calib, gaze, dots = [], [], []
    with open(os.path.join(spath, "events.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            e = json.loads(line)
            k, p = e["kind"], e.get("payload", {})
            if k == "calib":
                calib.append((p["features"], p["target"][0], p["target"][1],
                              p.get("crop")))
            elif k == "gaze" and p.get("features"):
                gaze.append((e["t_mono"], p["features"]))
            elif k == "dot":
                dots.append((e["t_mono"], tuple(p["pos"])))
    return calib, gaze, dots


def crop_vector(spath, stem):
    """24x16 grayscale L+R crops, flattened, standardized later."""
    stem = f"{stem:06d}" if isinstance(stem, int) else str(stem)
    vec = []
    for side in ("L", "R"):
        path = os.path.join(spath, "crops", f"{stem}_{side}.jpg")
        if not os.path.exists(path):
            return None
        im = Image.open(path).convert("L").resize((24, 16))
        vec.append(np.asarray(im, dtype=np.float64).ravel() / 255.0)
    return np.concatenate(vec)


def ridge_fit(X, Y, alpha):
    """Ridge with unpenalized bias. X: n d, Y: n 2. Returns (W, b)."""
    n, d = X.shape
    mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-9
    Xs = (X - mu) / sd
    A = np.vstack([Xs, np.sqrt(alpha) * np.eye(d)])
    B = np.vstack([Y - Y.mean(axis=0), np.zeros((d, 2))])
    W, *_ = np.linalg.lstsq(A, B, rcond=None)
    return (W / sd[:, None], Y.mean(axis=0) - (mu / sd) @ W, mu, sd)


def ridge_predict(X, model):
    W, b, _, _ = model
    return X @ W + b


def main():
    sessions = sorted(glob.glob(os.path.join("data", "sess-*")))
    sessions += sorted(glob.glob(os.path.join("data", "beta-*")))
    agg_base, agg_app = [], []
    for spath in sessions:
        calib, gaze, dots = load_session(spath)
        if len(calib) < 5:
            continue
        # Labeled pairs: (crop vec, features, target pos, group idx)
        pairs = []
        for ci, (feats, gx, gy, tag) in enumerate(calib):
            if tag:
                vec = crop_vector(spath, tag)
                if vec is not None:
                    pairs.append((vec, feats, (gx, gy), 1000 + ci))
        for gi_start in range(12, len(gaze) + 1, 12):
            t = gaze[gi_start - 1][0]
            for di, (td, pos) in enumerate(dots):
                if abs(t - td) <= 1.0:
                    vec = crop_vector(spath, gi_start)
                    if vec is not None:
                        pairs.append((vec, gaze[gi_start - 1][1], pos, di))
        if len({p[3] for p in pairs}) < 3:
            print(f"{spath}: only {len(pairs)} labeled crops, skipped")
            continue
        base = fit_calibration(calib)
        eb, ea = [], []
        for held in sorted({p[3] for p in pairs}):
            train = [p for p in pairs if p[3] != held]
            test = [p for p in pairs if p[3] == held]
            X = np.array([p[0] for p in train])
            Y = np.array([p[2] for p in train])
            model = ridge_fit(X, Y, alpha=50.0)
            for vec, feats, pos, _ in test:
                xb, yb = map_to_screen(feats, base)
                xa, ya = ridge_predict(vec[None, :], model)[0]
                eb.append(((xb - pos[0]) ** 2 + (yb - pos[1]) ** 2) ** 0.5)
                ea.append(((xa - pos[0]) ** 2 + (ya - pos[1]) ** 2) ** 0.5)
        mb = sum(eb) / len(eb)
        ma = sum(ea) / len(ea)
        agg_base += eb
        agg_app += ea
        print(f"{spath}: labeled={len(pairs)} "
              f"baseline={mb:.0f}px appearance={ma:.0f}px")
    if agg_base:
        mb = sum(agg_base) / len(agg_base)
        ma = sum(agg_app) / len(agg_app)
        print(f"\nPooled LODO: baseline={mb:.0f}px appearance={ma:.0f}px "
              f"(n={len(agg_base)} dot-crops)")
        print("T20 done. Adopt appearance only on a clear win.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
