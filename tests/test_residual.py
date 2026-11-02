"""Population residual field: learns a nonlinear residual, LOSO-shaped."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from gaze.residual import fit_residual, predict_residual


class TestResidual(unittest.TestCase):
    def test_learns_nonlinear_residual(self):
        rng = np.random.RandomState(7)
        X = rng.uniform(-1, 1, size=(120, 3))

        def truth(x):
            return np.array([80.0 * np.sin(2.0 * x[0]) + 30.0 * x[1],
                             60.0 * np.cos(2.0 * x[2])])

        Y = np.array([truth(x) for x in X])
        model = fit_residual(X[:90], Y[:90], lam=0.1)
        pred = predict_residual(model, X[90:])
        base = np.mean(np.hypot(Y[90:, 0], Y[90:, 1]))
        corr = np.mean(np.hypot(Y[90:, 0] - pred[:, 0],
                                Y[90:, 1] - pred[:, 1]))
        self.assertLess(corr, base * 0.5)

    def test_zero_residual_stays_zero(self):
        X = np.random.RandomState(1).uniform(-1, 1, size=(20, 2))
        model = fit_residual(X, np.zeros((20, 2)), lam=1.0)
        pred = predict_residual(model, [[0.1, -0.2]])
        self.assertAlmostEqual(float(abs(pred).max()), 0.0, places=9)


if __name__ == "__main__":
    unittest.main()
