"""Split conformal prediction (LAC — Least Ambiguous set-valued Classifier).

Nonconformity score for class k is ``s_k = 1 - p_k`` (one minus the calibrated
probability). On a patient-disjoint calibration set we compute the empirical
``(1-alpha)`` quantile ``qhat`` of the true-class scores (with the finite-sample
``ceil((n+1)(1-alpha))/n`` correction). The prediction set for a test window is
``{k : 1 - p_k <= qhat}  ==  {k : p_k >= 1 - qhat}``.

Under exchangeability (guaranteed here because calibration and test are patient-
disjoint), this yields marginal coverage ``P(y in set) >= 1 - alpha``.
"""

from __future__ import annotations

import numpy as np

from .._math import conformal_quantile
from ..schemas import ConformalResult


class SplitConformalPredictor:
    def __init__(self, alpha: float = 0.1, force_nonempty: bool = True):
        if not (0.0 < alpha < 1.0):
            raise ValueError("alpha must be in (0, 1)")
        self.alpha = float(alpha)
        # Clinically-safe variant: never emit an empty set — always include the
        # top-1 class when the score threshold would exclude everything. This can
        # only *increase* coverage, so the marginal guarantee P(y in set) >= 1-alpha
        # is preserved while avoiding the awkward "no prediction" output.
        self.force_nonempty = bool(force_nonempty)
        self.qhat: float = 1.0
        self._fitted = False
        self._n_calibration = 0

    @property
    def target_coverage(self) -> float:
        return 1.0 - self.alpha

    def fit(self, calib_probs: np.ndarray, calib_labels: np.ndarray) -> "SplitConformalPredictor":
        calib_probs = np.asarray(calib_probs, dtype=np.float64)
        y = np.asarray(calib_labels, dtype=int)
        true_p = calib_probs[np.arange(calib_probs.shape[0]), y]
        scores = 1.0 - true_p  # nonconformity of the true class
        self.qhat = conformal_quantile(scores, self.alpha)
        self._n_calibration = int(y.size)
        self._fitted = True
        return self

    def predict(self, probs: np.ndarray, class_names: tuple[str, ...]) -> ConformalResult:
        if not self._fitted:
            raise RuntimeError("conformal predictor not fitted")
        probs = np.asarray(probs, dtype=np.float64)
        threshold = 1.0 - self.qhat
        prediction_sets = probs >= threshold  # (N, K) bool
        if self.force_nonempty:
            empty = ~prediction_sets.any(axis=1)
            if np.any(empty):
                prediction_sets[empty, probs[empty].argmax(axis=1)] = True
        return ConformalResult(
            method="split_conformal_lac",
            alpha=self.alpha,
            target_coverage=self.target_coverage,
            qhat=self.qhat,
            prediction_sets=prediction_sets,
            class_names=tuple(class_names),
            n_calibration=self._n_calibration,
        )
