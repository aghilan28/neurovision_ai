"""Deterministic temperature scaling.

Temperature scaling fits a single scalar ``T > 0`` that divides the logits before
softmax, minimizing negative log-likelihood on a held-out (patient-disjoint)
calibration set. It is the simplest, most robust post-hoc calibrator and does not
change the argmax class (so accuracy is preserved while confidence is calibrated).

The fit is deterministic: a coarse log-spaced grid search followed by
golden-section refinement, with no randomness.
"""

from __future__ import annotations

import numpy as np

from .._math import softmax, negative_log_likelihood


class TemperatureScaler:
    def __init__(self) -> None:
        self.temperature: float = 1.0
        self._fitted = False

    def fit(self, logits: np.ndarray, labels: np.ndarray, lo: float = 0.05, hi: float = 10.0) -> "TemperatureScaler":
        logits = np.asarray(logits, dtype=np.float64)
        labels = np.asarray(labels, dtype=int)

        def nll(t: float) -> float:
            return negative_log_likelihood(softmax(logits / t), labels)

        # coarse log-spaced grid
        grid = np.geomspace(lo, hi, 40)
        best_t = float(grid[int(np.argmin([nll(t) for t in grid]))])

        # golden-section refinement around the best grid point
        a = max(lo, best_t / 1.5)
        b = min(hi, best_t * 1.5)
        gr = (np.sqrt(5.0) - 1.0) / 2.0
        c = b - gr * (b - a)
        d = a + gr * (b - a)
        fc, fd = nll(c), nll(d)
        for _ in range(60):
            if fc < fd:
                b, d, fd = d, c, fc
                c = b - gr * (b - a)
                fc = nll(c)
            else:
                a, c, fc = c, d, fd
                d = a + gr * (b - a)
                fd = nll(d)
            if abs(b - a) < 1e-6:
                break
        self.temperature = float((a + b) / 2.0)
        self._fitted = True
        return self

    def transform(self, logits: np.ndarray) -> np.ndarray:
        """Return calibrated probabilities ``softmax(logits / T)``."""
        return softmax(np.asarray(logits, dtype=np.float64) / self.temperature)
