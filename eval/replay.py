"""Offline replay of gaze strategies over recorded sessions. Stdlib only.

Strategy A: initial calibration only, no updates. Later strategies (B-D)
add corrections as functions of (features, anchors) and share this harness.
"""

from gaze.calibration import dot_error
from gaze.features import map_to_screen


def replay_a(events, matrix):
    """Apply the fixed calibration matrix to every gaze event.

    Returns list of (t_mono, predicted) for events of kind gaze with features.
    """
    out = []
    for e in events:
        if e["kind"] != "gaze" or not e["payload"].get("features"):
            continue
        pred = map_to_screen(e["payload"]["features"], matrix)
        out.append((e["t_mono"], pred))
    return out


def error_over_time(predictions, dots, window_s=0.0):
    """Match each dot to predictions near it. Returns [(t, err_px)].

    With window_s > 0, average every prediction within the window before
    scoring: single-frame predictions carry the measured noise, and a user
    fixating a dot emits a cloud, not a point. Falls back to the nearest
    prediction when the window is empty.
    """
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


def drift_slope(error_series):
    """Linear fit slope of error vs time (px per second). Returns (slope, intercept)."""
    n = len(error_series)
    if n < 2:
        return 0.0, error_series[0][1] if n else 0.0
    sx = sum(t for t, _ in error_series)
    sy = sum(e for _, e in error_series)
    sxx = sum(t * t for t, _ in error_series)
    sxy = sum(t * e for t, e in error_series)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.0, sy / n
    slope = (n * sxy - sx * sy) / denom
    return slope, (sy - slope * sx) / n


def summarize(error_series):
    """Mean error and drift slope for one strategy on one session."""
    if not error_series:
        return {"n": 0, "mean_px": 0.0, "slope_px_s": 0.0}
    slope, _ = drift_slope(error_series)
    return {
        "n": len(error_series),
        "mean_px": sum(e for _, e in error_series) / len(error_series),
        "slope_px_s": slope,
    }
