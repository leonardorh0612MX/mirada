"""Landmarks to gaze features to raw screen point. Pure functions, no I/O.

Input landmarks follow MediaPipe FaceLandmarker order: 478 points, each an
(x, y) pair in pixels. Indices used (established MediaPipe topology):
left eye corners 33/133, right eye corners 362/263, left iris 468-472,
right iris 473-477, nose tip 1, forehead 10, chin 152, cheeks 234/454.

Features v2 (7): [dxL, dyL, dxR, dyR, head_dx, head_dy, pitch].
Head features capture what the eyes alone miss: people turn their head
toward wide targets and the iris barely moves. Measured Oct 27: iris-only
features correlate 0.11-0.40 with horizontal gaze on a 27" monitor.
"""

LEFT_OUTER, LEFT_INNER = 33, 133
RIGHT_OUTER, RIGHT_INNER = 362, 263
LEFT_IRIS = (468, 469, 470, 471, 472)
RIGHT_IRIS = (473, 474, 475, 476, 477)
NOSE, FOREHEAD, CHIN, CHEEK_L, CHEEK_R = 1, 10, 152, 234, 454
N_LANDMARKS = 478
_MIN_EYE_WIDTH_PX = 5.0
_MIN_FACE_PX = 20.0


def _mean(points):
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


def _eye_offset(landmarks, outer, inner, iris_ids):
    """Iris offset from eye center, normalized by eye width. None if degenerate."""
    outer_p, inner_p = landmarks[outer], landmarks[inner]
    width = ((outer_p[0] - inner_p[0]) ** 2 + (outer_p[1] - inner_p[1]) ** 2) ** 0.5
    if width < _MIN_EYE_WIDTH_PX:
        return None
    center = ((outer_p[0] + inner_p[0]) / 2.0, (outer_p[1] + inner_p[1]) / 2.0)
    iris = _mean([landmarks[i] for i in iris_ids])
    return ((iris[0] - center[0]) / width, (iris[1] - center[1]) / width)


def _head_features(landmarks):
    """Nose position vs face box, plus a pitch proxy.

    Returns (head_dx, head_dy, pitch) or None if the face is degenerate.
    head_dx doubles as the yaw proxy (nose sideways drift).
    """
    cheek_l, cheek_r = landmarks[CHEEK_L], landmarks[CHEEK_R]
    forehead, chin = landmarks[FOREHEAD], landmarks[CHIN]
    nose = landmarks[NOSE]
    fw = cheek_r[0] - cheek_l[0]
    fh = chin[1] - forehead[1]
    if abs(fw) < _MIN_FACE_PX or abs(fh) < _MIN_FACE_PX:
        return None
    head_cx = (cheek_l[0] + cheek_r[0]) / 2.0
    head_cy = (forehead[1] + chin[1]) / 2.0
    head_dx = (nose[0] - head_cx) / fw
    head_dy = (nose[1] - head_cy) / fh
    eye_cy = (landmarks[LEFT_OUTER][1] + landmarks[RIGHT_OUTER][1]) / 2.0
    pitch = (nose[1] - eye_cy) / fh
    return (head_dx, head_dy, pitch)


def extract_features(landmarks):
    """Landmark list to (features, valid, reason). Never raises."""
    if not landmarks:
        return None, False, "no_face"
    if len(landmarks) < N_LANDMARKS:
        return None, False, "short_landmarks"
    left = _eye_offset(landmarks, LEFT_OUTER, LEFT_INNER, LEFT_IRIS)
    right = _eye_offset(landmarks, RIGHT_OUTER, RIGHT_INNER, RIGHT_IRIS)
    if left is None or right is None:
        return None, False, "degenerate_eye"
    head = _head_features(landmarks)
    if head is None:
        return None, False, "degenerate_face"
    feats = [left[0], left[1], right[0], right[1], *head]
    if any(v != v or abs(v) == float("inf") for v in feats):
        return None, False, "nonfinite"
    return feats, True, "ok"


# Fixed physical scales (pooled across the Oct 28 beta sessions). Never
# re-estimated per fit: dividing by a near-zero calibration std made the
# same coefficient mean different things on every refit (Wonder Q2).
FIXED_SCALES = [0.045, 0.022, 0.055, 0.020, 0.040, 0.025, 0.025]


def standardize(features, means, scales=FIXED_SCALES):
    """(f - mu) / s with fixed scales. means come from the fit samples."""
    return [(f - m) / s for f, m, s in zip(features, means, scales)]


def expand_features(z):
    """Bilinear + quadratic expansion of standardized 7-features (Q1).

    Head rotation acts multiplicatively on the gaze ray, so the leading
    correction is e x h, plus own-squares for projection curvature.
    z = [dxL, dyL, dxR, dyR, head_dx, head_dy, pitch]; eye = mean(L, R).
    Returns 15 terms: 7 main + 4 interactions + 4 squares.
    """
    ex = (z[0] + z[2]) / 2.0
    ey = (z[1] + z[3]) / 2.0
    hx, hy = z[4], z[5]
    return list(z) + [ex * hx, ex * hy, ey * hx, ey * hy,
                      ex * ex, ey * ey, hx * hx, hy * hy]


def map_to_screen(features, matrix):
    """Affine map: screen = M @ [features..., 1]. M is 2x(k+1)."""
    v = list(features) + [1.0]
    if len(matrix[0]) != len(v):
        raise ValueError(f"matrix width {len(matrix[0])} != features+1 {len(v)}")
    x = sum(matrix[0][j] * v[j] for j in range(len(v)))
    y = sum(matrix[1][j] * v[j] for j in range(len(v)))
    return (x, y)
