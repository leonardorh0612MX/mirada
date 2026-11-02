"""Population residual field (T27). Numpy only.

A frozen Gaussian-basis (kernel-ridge) field over geometric gaze
features, learned offline from pooled recorded sessions: it predicts
the base map's residual (dx, dy) for a feature vector. Live, only the
affine stage keeps adapting; this field never updates online and never
sees eye pixels - features only, so no biometric imagery is stored in
the model. Trained/tested strictly leave-one-session-out in
tools/t27_residual.py.
"""

import numpy as np


def _standardize_fit(X):
    X = np.asarray(X, dtype=float)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd < 1e-9] = 1.0
    return mu, sd


def _kernel(A, B, sigma):
    A = np.atleast_2d(np.asarray(A, dtype=float))
    B = np.atleast_2d(np.asarray(B, dtype=float))
    d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(axis=2)
    return np.exp(-d2 / (2.0 * sigma * sigma))


def median_sigma(X):
    """Median pairwise distance of standardized X (bandwidth prior)."""
    X = np.atleast_2d(np.asarray(X, dtype=float))
    if len(X) < 2:
        return 1.0
    d2 = ((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2)
    iu = np.triu_indices(len(X), k=1)
    med = float(np.median(np.sqrt(d2[iu])))
    return med if med > 1e-9 else 1.0


def fit_residual(X, Y, sigma=None, lam=1.0):
    """Fit kernel-ridge residuals. X: (n, d) features, Y: (n, 2)."""
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)
    mu, sd = _standardize_fit(X)
    Z = (X - mu) / sd
    if sigma is None:
        sigma = median_sigma(Z)
    K = _kernel(Z, Z, sigma)
    alpha = np.linalg.solve(K + lam * np.eye(len(Z)), Y)
    return {"X": Z, "alpha": alpha, "mu": mu, "sd": sd,
            "sigma": float(sigma), "lam": float(lam)}


def predict_residual(model, X):
    """Predicted (dx, dy) residual per feature row."""
    X = np.atleast_2d(np.asarray(X, dtype=float))
    Z = (X - model["mu"]) / model["sd"]
    return _kernel(Z, model["X"], model["sigma"]) @ model["alpha"]
