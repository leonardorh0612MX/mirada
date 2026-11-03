"""Anchor-gated online gaze correction. Stdlib only, no I/O.

Three gates in order: confidence, residual, age. One anchor never moves the
model much: RLS with a strong calibration prior and a forgetting factor.
Every proposal returns a verdict so the caller can log it in the ledger.
"""

from .rls import RLSFilter

def _with_bias(features):
    return list(features) + [1.0]


class _AxisRLS:
    """2-param RLS for one output axis: offset = w0 + w1 * head_feature."""

    def __init__(self, lam=0.995, p0=1.0):
        self.lam = lam
        self.w = [0.0, 0.0]
        self.P = [[p0, 0.0], [0.0, p0]]

    def offset(self, h):
        return self.w[0] + self.w[1] * h

    def update(self, h, target_offset, weight):
        phi = [1.0, h]
        pphi = [self.P[0][0] * phi[0] + self.P[0][1] * phi[1],
                self.P[1][0] * phi[0] + self.P[1][1] * phi[1]]
        denom = self.lam / max(weight, 1e-6) + phi[0] * pphi[0] + phi[1] * pphi[1]
        k = [pphi[0] / denom, pphi[1] / denom]
        err = target_offset - self.offset(h)
        self.w[0] += k[0] * err
        self.w[1] += k[1] * err
        self.P = [[(self.P[i][j] - k[i] * pphi[j]) / self.lam for j in range(2)]
                  for i in range(2)]

    def update_intercept(self, h, target_offset, weight):
        """Bias-only step: slope stays frozen at its current value."""
        self.w[0] += weight * (target_offset - self.offset(h))


class BiasCorrector:
    """Online correction restricted to bias + head-coupled drift (Q2/Q4).

    The base map is never re-fit online. Anchors only move a 4-param
    offset delta = (bx + cx*hx, by + cy*hy), and only by consensus:
    3 of the last 5 implied biases must agree within 75 px. Soft weight
    w = 1/(1+(r/150)^2); residual > 3*MAD-scale is flagged, not applied.
    Trust region: <=25 px shift per update at the anchor.
    """

    def __init__(self, base_predict, means, lam=0.995,
                 consensus_n=5, consensus_k=3, consensus_radius=75.0,
                 sample_feats=None, certain_bias_only=False, trust_px=25.0):
        self.base_predict = base_predict
        self.means = means
        # Board mode: certain anchors move ONLY the bias (slope frozen).
        # Full slope updates let every selection re-tilt the head-coupled
        # plane, so correct selections progressively warped neighbours
        # (web-20261101-210049: 6 applied, residuals never shrank).
        self.certain_bias_only = certain_bias_only
        self.trust_px = trust_px
        # Appearance mode passes opaque samples (crop vec, feats): head
        # channels still come from the 7-feature half. Default keeps the
        # sample itself as features (linear mode, unchanged behavior).
        self._sample_feats = sample_feats or (lambda s: s)
        self.ax = _AxisRLS(lam=lam)
        self.ay = _AxisRLS(lam=lam)
        self.consensus_n = consensus_n
        self.consensus_k = consensus_k
        self.consensus_radius = consensus_radius
        self._buffer = []  # (features, anchor, bias)
        self._residuals = []

    def _head(self, features):
        return ((features[4] - self.means[4]) / 0.04,
                (features[5] - self.means[5]) / 0.025)

    def _head_of(self, sample):
        return self._head(self._sample_feats(sample))

    def predict(self, features):
        bx, by = self.base_predict(features)
        hx, hy = self._head_of(features)
        return (bx + self.ax.offset(hx), by + self.ay.offset(hy))

    def _sigma(self):
        rs = sorted(self._residuals[-20:])
        if len(rs) < 5:
            return 120.0
        med = rs[len(rs) // 2]
        mad = sorted(abs(r - med) for r in rs)[len(rs) // 2]
        return max(120.0, 1.4826 * mad)

    def _apply(self, feats, anch, r, bias_only=False, sigma_px=0.0):
        w = 1.0 / (1.0 + (r / 150.0) ** 2)
        # Coarse label: a selection says "somewhere in this tile", not
        # "exactly at its centre". Scale the step by the tile's own
        # uncertainty so huge cells teach slowly and small keys faster.
        w *= 150.0 / (150.0 + max(sigma_px, 0.0))
        hx, hy = self._head_of(feats)
        before = (self.ax.offset(hx), self.ay.offset(hy))
        pbx, pby = self.base_predict(feats)
        if bias_only:
            self.ax.update_intercept(hx, anch[0] - pbx, w)
            self.ay.update_intercept(hy, anch[1] - pby, w)
        else:
            self.ax.update(hx, anch[0] - pbx, w)
            self.ay.update(hy, anch[1] - pby, w)
        after = (self.ax.offset(hx), self.ay.offset(hy))
        shift = ((after[0] - before[0]) ** 2 + (after[1] - before[1]) ** 2) ** 0.5
        if shift > self.trust_px:  # trust region: rescale the step back
            f = self.trust_px / shift
            self._rescale(before, after, f, hx, hy)
        return w, min(shift, self.trust_px)

    def update(self, features, anchor, certain=False, sigma_px=0.0):
        """Propose an anchor. Returns (state, info).

        state: 'waiting' (no consensus yet), 'applied', 'flagged'
        (residual outlier). Info carries residual and soft weight.
        certain=True is a deliberate user action (0.5-0.6 s hold on a
        chosen target): the LABEL is certain, the map is what's wrong,
        so it applies directly. Consensus across different targets is
        unreachable anyway: error is regional, each target implies a
        different bias (board 20261029-163748: waiting:285,
        flagged:427, waiting:89, zero applied). Soft weight + trust
        region bound a wrong target to <=25 px.
        sigma_px is the anchor's own position noise (tile half-size for
        selections): coarse labels step smaller per update and converge
        across repeats instead of jumping to a 2-3 cm-off point.
        """
        bx, by = self.base_predict(features)
        bias = (anchor[0] - bx, anchor[1] - by)
        r = (bias[0] ** 2 + bias[1] ** 2) ** 0.5
        self._residuals.append(r)
        if certain:
            if self.certain_bias_only and r > 3.0 * self._sigma():
                # Warp-scale residual: bias cannot fix this; flag it for
                # recalibration instead of chasing it across the screen.
                return "flagged", {"residual": r, "certain": True}
            w, shift = self._apply(features, anchor, r,
                                   bias_only=self.certain_bias_only,
                                   sigma_px=sigma_px)
            return "applied", {"residual": r, "weight": w, "shift": shift,
                               "certain": True}
        flagged = r > 3.0 * self._sigma()
        # Flagged anchors still join the buffer: 3 agreeing "outliers" are
        # genuine drift, not noise. Consensus + trust region protect us.
        self._buffer.append((features, anchor, bias))
        self._buffer = self._buffer[-self.consensus_n:]
        if len(self._buffer) < self.consensus_k:
            return ("flagged" if flagged else "waiting"), {"residual": r}
        med = (sorted(b[2][0] for b in self._buffer)[len(self._buffer) // 2],
               sorted(b[2][1] for b in self._buffer)[len(self._buffer) // 2])
        near = [b for b in self._buffer
                if ((b[2][0] - med[0]) ** 2 + (b[2][1] - med[1]) ** 2) ** 0.5
                <= self.consensus_radius]
        if len(near) < self.consensus_k:
            return "waiting", {"residual": r}
        feats, anch, _ = near[len(near) // 2]
        w, shift = self._apply(feats, anch, r)
        self._buffer = []
        return "applied", {"residual": r, "weight": w, "shift": shift}

    def _rescale(self, before, after, f, hx, hy):
        # Recompute w so offset lands at before + f*(after-before).
        for axis, b, a, h in ((self.ax, before[0], after[0], hx),
                              (self.ay, before[1], after[1], hy)):
            axis.w[1] = axis.w[1]  # slope kept; solve intercept for target
            axis.w[0] = (b + f * (a - b)) - axis.w[1] * h


class Corrector:
    def __init__(self, calibration_matrix, lam=0.98, p0=1e-3,
                 min_confidence=0.5, max_residual_px=150.0, max_age_s=10.0):
        dim = len(calibration_matrix[0])
        self.fx = RLSFilter(dim, lam=lam, p0=p0, w_init=calibration_matrix[0])
        self.fy = RLSFilter(dim, lam=lam, p0=p0, w_init=calibration_matrix[1])
        self.min_confidence = min_confidence
        self.max_residual_px = max_residual_px
        self.max_age_s = max_age_s

    def predict(self, features):
        x = _with_bias(features)
        return (self.fx.predict(x), self.fy.predict(x))

    def update(self, features, anchor, confidence, anchor_age_s,
                 sample_weight=1.0):
        """Propose one anchor. Returns (accepted, reason).

        anchor: (x, y) screen point. anchor_age_s: seconds since the anchor
        was produced. Rejections never touch the filters. sample_weight
        scales the RLS step for accepted anchors (Huber-IRLS).
        """
        if confidence < self.min_confidence:
            return False, "low_confidence"
        if anchor_age_s > self.max_age_s:
            return False, "stale"
        pred = self.predict(features)
        residual = ((pred[0] - anchor[0]) ** 2 + (pred[1] - anchor[1]) ** 2) ** 0.5
        if residual > self.max_residual_px:
            return False, "large_residual"
        x = _with_bias(features)
        self.fx.update(x, anchor[0], weight=sample_weight)
        self.fy.update(x, anchor[1], weight=sample_weight)
        return True, "applied"
