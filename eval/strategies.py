"""Replay strategies B-D over recorded sessions. Stdlib only.

All strategies share the harness: walk gaze events in time order, apply due
anchors through a gated Corrector, predict, match dots. Strategy A lives in
eval/replay.py (no updates at all). Anchor feeds come from the session in
T13; here synthetic feeds prove the comparison logic.
"""

from gaze.calibration import dot_error
from corrector.corrector import Corrector


def run_strategy(events, dots, matrix, anchors, **corrector_kw):
    """events: gaze dicts with features. anchors: [(t, x, y, conf, source)].

    Returns (predictions, ledger_like): predictions is [(t, (x, y))],
    ledger_like is [(anchor, accepted, reason)] for every anchor consumed.
    """
    anchors = sorted(anchors, key=lambda a: a[0])
    corrector = Corrector(matrix, **corrector_kw)
    predictions, log, ai = [], [], 0
    for e in events:
        if e["kind"] != "gaze" or not e["payload"].get("features"):
            continue
        t = e["t_mono"]
        feats = e["payload"]["features"]
        while ai < len(anchors) and anchors[ai][0] <= t:
            ta, ax, ay, conf, _ = anchors[ai]
            ok, reason = corrector.update(feats, (ax, ay), conf, t - ta)
            log.append((anchors[ai], ok, reason))
            ai += 1
        predictions.append((t, corrector.predict(feats)))
    return predictions, log


def error_over_time(predictions, dots, window_s=0.0):
    out = []
    for t_dot, pos in dots:
        near = [p for t, p in predictions if abs(t - t_dot) <= window_s]
        if near:
            pred = (sum(p[0] for p in near) / len(near),
                    sum(p[1] for p in near) / len(near))
        else:
            best = min(predictions, key=lambda p: abs(p[0] - t_dot), default=None)
            if best is None:
                continue
            pred = best[1]
        out.append((t_dot, dot_error(pred, pos)))
    return out


def mean_error(series):
    return sum(e for _, e in series) / len(series) if series else float("nan")
