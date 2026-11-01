"""Synthetic sessions with known drift for replay verification. Stdlib only.

The synthetic user fixates each dot. Features encode the dot position plus a
drift term that grows linearly in time, which the fixed calibration cannot
see. Strategy A must report a slope matching the injected drift. Real
sessions replace this generator in T13.
"""

from gaze.calibration import dot_schedule

ANCHOR_EVERY_S = 4.0

TRUE_M = [[400.0, 50.0, 400.0, -50.0, 960.0], [30.0, 300.0, -30.0, 300.0, 540.0]]
SCREEN = (1920, 1080)
DOT = (960.0, 540.0)


def make_session(duration_s=600.0, drift_px_s=0.05, gaze_every_s=0.5):
    """Returns (matrix, events, dots). Drift enters through the features."""
    matrix = [row[:] for row in TRUE_M]
    gain = matrix[0][0] + matrix[0][2]  # px of x-error per unit of dx drift
    events, dots = [], []
    t, i = 0.0, 0
    dot_times = dot_schedule(duration_s)
    dot_idx = 0
    while t < duration_s:
        k = (drift_px_s * t) / gain
        feats = [k, 0.0, k, 0.0]
        events.append({"t_mono": t, "kind": "gaze", "payload": {"features": feats}})
        if dot_idx < len(dot_times) and t >= dot_times[dot_idx]:
            dots.append((dot_times[dot_idx], list(DOT)))
            events.append({"t_mono": dot_times[dot_idx], "kind": "dot",
                           "payload": {"pos": list(DOT)}})
            dot_idx += 1
        t += gaze_every_s
        i += 1
    return matrix, events, dots


def make_anchors(duration_s=600.0, noise_px=8.0, every_s=ANCHOR_EVERY_S, conf=0.8):
    """Synthetic semantic anchors: near the dot, small deterministic noise.

    noise_px=8 mimics app-event anchors (strategy C). Tighter noise mimics
    SAM-localized anchors (strategy D). Clicks (strategy B) use sparse,
    exact anchors via every_s=120 and noise 0.
    """
    anchors, t, i = [], 0.0, 0
    while t < duration_s:
        nx = ((i * 37) % 17 - 8) / 8.0 * noise_px
        ny = ((i * 53) % 13 - 6) / 6.0 * noise_px
        anchors.append((t, DOT[0] + nx, DOT[1] + ny, conf, "synthetic"))
        t += every_s
        i += 1
    return anchors
