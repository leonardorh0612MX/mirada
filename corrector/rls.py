"""Recursive least squares with forgetting. Stdlib only, no I/O.

One filter per screen axis. Weights init at the calibration row (strong
prior). P0 scales trust in that prior: small p0 adapts slowly, large p0
relearns fast. Lambda forgets old evidence so drift never fossilizes.
"""


class RLSFilter:
    def __init__(self, dim, lam=0.98, p0=1e-3, w_init=None):
        if not 0.0 < lam <= 1.0:
            raise ValueError(f"lam must be in (0, 1], got {lam}")
        self.dim = dim
        self.lam = lam
        self.w = list(w_init) if w_init else [0.0] * dim
        if len(self.w) != dim:
            raise ValueError(f"w_init length {len(self.w)} != dim {dim}")
        self.p = [[p0 if i == j else 0.0 for j in range(dim)] for i in range(dim)]

    def predict(self, x):
        return sum(wi * xi for wi, xi in zip(self.w, x))

    def update(self, x, y, weight=1.0):
        """One RLS step. Returns the prior prediction error (residual).

        weight in (0, 1] downweights suspect samples (Huber-IRLS style):
        the measurement-noise term scales as lam/weight.
        """
        pred = self.predict(x)
        err = y - pred
        # gain k = P x / (lam/w + x^T P x)
        px = [sum(self.p[i][j] * x[j] for j in range(self.dim)) for i in range(self.dim)]
        denom = self.lam / max(weight, 1e-6) + sum(x[i] * px[i] for i in range(self.dim))
        k = [v / denom for v in px]
        self.w = [wi + ki * err for wi, ki in zip(self.w, k)]
        # P = (P - k x^T P) / lam
        self.p = [[(self.p[i][j] - k[i] * px[j]) / self.lam for j in range(self.dim)]
                  for i in range(self.dim)]
        return err
