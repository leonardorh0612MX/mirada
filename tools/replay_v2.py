"""T14 v2: decisive replay on one recorded session.

Strategies on identical data:
  A-legacy : stored calibration matrix, no anchors (what Oct 27 shipped)
  A-refit  : today's standardized fit on stored calib samples, no anchors
  C-cons   : refit + BiasCorrector (soft weight, consensus) fed Spark anchors

Usage: .\\.venv\\Scripts\\python.exe tools\\replay_v2.py data\\sess-XXXX
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corrector.corrector import BiasCorrector  # noqa: E402
from corrector.rls import RLSFilter  # noqa: E402
from eval.strategies import (  # noqa: E402
    error_over_time,
    mean_error,
    run_strategy,
)
from gaze.calibration import fit_calibration  # noqa: E402
from gaze.features import map_to_screen  # noqa: E402


def run_consensus(events, refit, means, feed):
    """BiasCorrector over time-ordered gaze; returns (series, states)."""
    bc = BiasCorrector(lambda f: map_to_screen(f, refit), means)
    feed = sorted(feed, key=lambda a: a[0])
    preds, states, ai = [], [], 0
    for e in events:
        if e["kind"] != "gaze" or not e["payload"].get("features"):
            continue
        t, feats = e["t_mono"], e["payload"]["features"]
        while ai < len(feed) and feed[ai][0] <= t:
            stt, info = bc.update(feats, (feed[ai][1], feed[ai][2]))
            states.append((stt, round(info.get("residual", 0))))
            ai += 1
        preds.append((t, bc.predict(feats)))
    return preds, states


def run_batch4(events, refit, feed, huber_px=150.0, batch=4, p0=0.05):
    """GazeAgent-style: full-RLS anchors applied at batch boundaries.

    Anchors buffer until `batch` accumulate, then all apply with Huber
    weights w=min(1, huber/r). One-step-ahead holds by construction: dots
    never enter the fit, and predictions at time t use anchors older than t.
    """
    def with_bias(features):
        return list(features) + [1.0]

    fx = RLSFilter(len(refit[0]), lam=0.98, p0=p0, w_init=refit[0])
    fy = RLSFilter(len(refit[0]), lam=0.98, p0=p0, w_init=refit[1])
    feed = sorted(feed, key=lambda a: a[0])
    preds, buf, ai, applied = [], [], 0, 0
    for e in events:
        if e["kind"] != "gaze" or not e["payload"].get("features"):
            continue
        t, feats = e["t_mono"], e["payload"]["features"]
        while ai < len(feed) and feed[ai][0] <= t:
            buf.append((feed[ai], feats))
            ai += 1
        if len(buf) >= batch:
            for (ta, ax, ay, *_), fbuf in buf:
                x = with_bias(fbuf)
                pred = (fx.predict(x), fy.predict(x))
                r = ((pred[0] - ax) ** 2 + (pred[1] - ay) ** 2) ** 0.5
                w = min(1.0, huber_px / max(r, 1e-9))
                fx.update(x, ax, weight=w)
                fy.update(x, ay, weight=w)
                applied += 1
            buf = []
        x = with_bias(feats)
        preds.append((t, (fx.predict(x), fy.predict(x))))
    return preds, applied


def corrupt_feed(feed, rho, seed):
    """Permute anchor positions over a rho fraction (seeded, deterministic)."""
    import random

    feed = sorted(feed, key=lambda a: a[0])
    rnd = random.Random(seed)
    idx = [i for i in range(len(feed)) if rnd.random() < rho]
    pts = [feed[i][1:3] for i in idx]
    rnd.shuffle(pts)
    out = [list(a) for a in feed]
    for i, (ax, ay) in zip(idx, pts):
        out[i][1], out[i][2] = ax, ay
    return [tuple(a) for a in out]


def load(spath):
    matrix, calib, gaze, dots = None, [], [], []
    with open(os.path.join(spath, "events.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            e = json.loads(line)
            k, p = e["kind"], e.get("payload", {})
            if k == "calibration_matrix":
                matrix = p["matrix"]
            elif k == "calib":
                calib.append((p["features"], p["target"][0], p["target"][1]))
            elif k == "gaze" and p.get("features"):
                gaze.append((e["t_mono"], p["features"]))
            elif k == "dot":
                dots.append((e["t_mono"], tuple(p["pos"])))
    anchors = {}
    apath = os.path.join(spath, "anchors_offline.json")
    if os.path.exists(apath):
        raw = json.load(open(apath))
        anchors = raw if isinstance(raw, dict) else {"C": raw}
    return matrix, calib, gaze, dots, anchors


def slope(series):
    if len(series) < 2:
        return float("nan")
    t0 = series[0][0]
    xs = [t - t0 for t, _ in series]
    ys = [e for _, e in series]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs) or 1.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def main():
    spath = sys.argv[1]
    matrix, calib, gaze, dots, anchors = load(spath)
    refit = fit_calibration(calib)
    k = len(calib[0][0])
    means = [sum(s[0][j] for s in calib) / len(calib) for j in range(k)]
    print(f"{spath}: calib={len(calib)} gaze={len(gaze)} dots={len(dots)}")

    def run(predict_at):
        preds = [(t, predict_at(t, f)) for t, f in gaze]
        return error_over_time(preds, dots, window_s=1.0)

    out = {}
    out["A-legacy"] = run(lambda t, f: map_to_screen(f, matrix))
    out["A-refit"] = run(lambda t, f: map_to_screen(f, refit))

    events = [{"t_mono": t, "kind": "gaze", "payload": {"features": f}}
              for t, f in gaze]
    for name in ("C", "D"):
        feed = sorted(anchors.get(name, []), key=lambda a: a[0])
        if not feed:
            continue
        preds, states = run_consensus(events, refit, means, feed)
        out[f"{name}-cons"] = error_over_time(preds, dots, window_s=1.0)
        print(f"{name}: {len(feed)} anchors -> {states}")

    print(f"\n{'dot':>10} " + " ".join(f"{k:>10}" for k in out))
    for i in range(len(dots)):
        row = []
        for k, series in out.items():
            row.append(f"{series[i][1]:10.0f}" if i < len(series) else " " * 10)
        print(f"{i:>10} " + " ".join(row))
    print()
    for k, series in out.items():
        print(f"{k}: mean={mean_error(series):.0f}px slope={slope(series):.3f}px/s")

    # T28: batch-of-4 one-step-ahead Huber updates + corruption ablation.
    feed_c = sorted(anchors.get("C", []), key=lambda a: a[0])
    if feed_c:
        preds_b4, n_applied = run_batch4(events, refit, feed_c)
        s_b4 = error_over_time(preds_b4, dots, window_s=1.0)
        print(f"\nT28 batch4: applied={n_applied} "
              f"mean={mean_error(s_b4):.0f}px slope={slope(s_b4):+.3f}px/s")
        print(f"{'rho':>6} {'gated':>8} {'forced':>8} "
              f"{'consensus':>9} {'batch4':>8}   (mean px)")
        for rho in (0.0, 0.10, 0.25, 0.50):
            corr = corrupt_feed(feed_c, rho, seed=7)
            pg, _ = run_strategy(events, dots, refit, corr)
            pf, _ = run_strategy(events, dots, refit, corr,
                                 max_residual_px=1e9, p0=0.05)
            pc, _ = run_consensus(events, refit, means, corr)
            pb, _ = run_batch4(events, refit, corr)
            row = [error_over_time(p, dots, window_s=1.0) for p in (pg, pf, pc, pb)]
            print(f"{rho:>6.2f} " + " ".join(f"{mean_error(s):>8.0f}" for s in row))
    return 0


if __name__ == "__main__":
    sys.exit(main())
