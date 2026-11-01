"""Initial calibration and dot ground-truth protocol. Pure functions, no I/O.

Calibration fits the 2x5 affine matrix used by gaze.features.map_to_screen:
screen = M @ [dxL, dyL, dxR, dyR, 1], solved per axis by least squares over
calibration samples. Dots are the ground truth for eval (EVAL.md).
"""

CALIBRATION_GRID = [
    (fx, fy)
    for fy in (0.08, 0.36, 0.64, 0.92)
    for fx in (0.08, 0.36, 0.64, 0.92)
]
DOT_EVERY_S = 120.0


def _solve_least_squares(rows, targets, ridge_alpha=1e-7):
    """Solve min ||A x - b|| via normal equations + Gaussian elimination.

    rows: list of feature rows (each length k). targets: list of floats.
    ridge_alpha: scalar, or per-column list (last entry ignored: the bias
    term is never penalized). Returns coefficient list of length k.
    Raises ValueError on singularity.
    """
    k = len(rows[0])
    ridge = ridge_alpha if isinstance(ridge_alpha, (list, tuple)) \
        else [ridge_alpha] * (k - 1) + [0.0]
    ata = [[0.0] * k for _ in range(k)]
    atb = [0.0] * k
    for r, t in zip(rows, targets):
        for i in range(k):
            atb[i] += r[i] * t
            for j in range(k):
                ata[i][j] += r[i] * r[j]
    for i in range(k - 1):
        ata[i][i] += ridge[i]
    n = k
    aug = [ata[i] + [atb[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda rr: abs(aug[rr][col]))
        if abs(aug[piv][col]) < 1e-12:
            raise ValueError("singular calibration matrix")
        aug[col], aug[piv] = aug[piv], aug[col]
        for rr in range(n):
            if rr != col:
                f = aug[rr][col] / aug[col][col]
                for c in range(col, n + 1):
                    aug[rr][c] -= f * aug[col][c]
    return [aug[i][n] / aug[i][i] for i in range(n)]


def fit_calibration(samples, ridge_alpha=25.0):
    """Samples: list of (features, screen_x, screen_y). Returns 2x(k+1) matrix.

    Feature columns are standardized before solving (normal equations square
    the condition number, and raw features ~0.1 vs targets ~3000px make the
    unscaled fit amplify live noise into hundred-px jumps). The scaling is
    folded back into the coefficients, so the returned matrix keeps the exact
    same format: screen = M @ [features..., 1].
    """
    if len(samples) < 5:
        raise ValueError(f"need >=5 samples, got {len(samples)}")
    k = len(samples[0][0])
    means, stds = [], []
    for j in range(k):
        col = [s[0][j] for s in samples]
        mu = sum(col) / len(col)
        var = sum((v - mu) ** 2 for v in col) / len(col)
        means.append(mu)
        stds.append(var ** 0.5 if var > 1e-24 else 1.0)
    rows = [[(s[0][j] - means[j]) / stds[j] for j in range(k)] + [1.0]
            for s in samples]

    def unfold(coef):
        out = [coef[j] / stds[j] for j in range(k)]
        out.append(coef[k] - sum(coef[j] * means[j] / stds[j] for j in range(k)))
        return out

    mx = unfold(_solve_least_squares(rows, [s[1] for s in samples],
                                     ridge_alpha=ridge_alpha))
    my = unfold(_solve_least_squares(rows, [s[2] for s in samples],
                                     ridge_alpha=ridge_alpha))
    return [mx, my]


def resubstitution_error(samples, matrix):
    """Mean px error of the fit on its own calibration samples."""
    from gaze.features import map_to_screen

    if not samples:
        return float("inf")
    total = 0.0
    for feats, gx, gy in samples:
        px, py = map_to_screen(feats, matrix)
        total += ((px - gx) ** 2 + (py - gy) ** 2) ** 0.5
    return total / len(samples)


class GazeMap:
    """Standardize (fixed scales) -> bilinear expansion -> linear map.

    Holds the enrollment means; prediction applies the same transform the
    fit used. to_dict()/from_dict() for session logging and replay.
    """

    def __init__(self, means, matrix):
        self.means = list(means)
        self.matrix = matrix

    def predict(self, features):
        from gaze.features import expand_features, map_to_screen, standardize

        return map_to_screen(expand_features(standardize(features, self.means)),
                             self.matrix)

    def to_dict(self):
        return {"means": self.means, "matrix": self.matrix}

    @classmethod
    def from_dict(cls, d):
        return cls(d["means"], d["matrix"])


def fit_gaze_map(samples, ridge_main=5.0, ridge_inter=25.0):
    """Fit a GazeMap: fixed-scale standardization + bilinear expansion.

    Group ridge (Wonder Q2): main effects penalized at ridge_main,
    interaction/square terms harder at ridge_inter. Samples are
    (features7, screen_x, screen_y).
    """
    from gaze.features import FIXED_SCALES, expand_features, standardize

    if len(samples) < 5:
        raise ValueError(f"need >=5 samples, got {len(samples)}")
    k = len(samples[0][0])
    means = [sum(s[0][j] for s in samples) / len(samples) for j in range(k)]
    scales = FIXED_SCALES if k == len(FIXED_SCALES) else [1.0] * k
    rows = [expand_features(standardize(s[0], means, scales)) + [1.0]
            for s in samples]
    n_main = k
    ridge = [ridge_main] * n_main + [ridge_inter] * (len(rows[0]) - 1 - n_main) + [0.0]
    mx = _solve_least_squares(rows, [s[1] for s in samples], ridge_alpha=ridge)
    my = _solve_least_squares(rows, [s[2] for s in samples], ridge_alpha=ridge)
    return GazeMap(means, [mx, my])


def calibration_points(screen_w, screen_h):
    """Grid points in pixels for the calibration stare sequence."""
    return [(fx * screen_w, fy * screen_h) for fx, fy in CALIBRATION_GRID]


def dot_schedule(duration_s, every_s=DOT_EVERY_S):
    """Dot onset times in seconds, starting after the first interval."""
    t, out = every_s, []
    while t < duration_s:
        out.append(t)
        t += every_s
    return out


def dot_error(predicted, dot):
    """Euclidean error in px between a gaze point and the dot position."""
    return ((predicted[0] - dot[0]) ** 2 + (predicted[1] - dot[1]) ** 2) ** 0.5
