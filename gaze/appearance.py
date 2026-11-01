"""Per-session appearance gaze map: ridge on eye-crop pixels. Numpy + PIL.

Geometry MUST match training exactly (tools/record_session.save_eye_crops
plus tools/t20_appearance.crop_vector): bbox over corner + iris landmarks
with a 12 px pad, 24x16 grayscale, /255, L+R concatenated (768-dim).
The live path replicates the training ops call-for-call, including
PIL-from-BGR channel order and default resample: any deviation is
train/serve skew on the model's only input.
"""

import numpy as np
from PIL import Image

LEFT_IDS = (33, 133, 468, 469, 470, 471, 472)
RIGHT_IDS = (362, 263, 473, 474, 475, 476, 477)
PAD = 12
W, H = 24, 16


def _crop(frame, lms, ids):
    h, w = frame.shape[:2]
    xs = [lms[i][0] for i in ids]
    ys = [lms[i][1] for i in ids]
    x1, x2 = max(0, int(min(xs) - PAD)), min(w, int(max(xs) + PAD))
    y1, y2 = max(0, int(min(ys) - PAD)), min(h, int(max(ys) + PAD))
    if x2 - x1 < 10 or y2 - y1 < 6:
        return None
    return frame[y1:y2, x1:x2]


def vector_from_frame(frame, lms):
    """768-dim L+R eye vector, or None when either eye is unusable."""
    try:
        parts = []
        for ids in (LEFT_IDS, RIGHT_IDS):
            crop = _crop(frame, lms, ids)
            if crop is None or crop.size == 0:
                return None
            im = Image.fromarray(crop).convert("L").resize((W, H))
            parts.append(np.asarray(im, dtype=np.float64).ravel() / 255.0)
        return np.concatenate(parts)
    except Exception:
        return None


def ridge_fit(X, Y, alpha=50.0):
    """Ridge with unpenalized bias. X: n d, Y: n 2. Returns (W, b, mu, sd)."""
    mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-9
    Xs = (X - mu) / sd
    A = np.vstack([Xs, np.sqrt(alpha) * np.eye(X.shape[1])])
    B = np.vstack([Y - Y.mean(axis=0), np.zeros((X.shape[1], 2))])
    W, *_ = np.linalg.lstsq(A, B, rcond=None)
    return (W / sd[:, None], Y.mean(axis=0) - (mu / sd) @ W, mu, sd)


def ridge_predict(X, model):
    W, b, _, _ = model
    return X @ W + b
