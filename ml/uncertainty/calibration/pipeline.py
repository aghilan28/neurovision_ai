"""Deterministic calibration pipeline.

Fits temperature scaling on a patient-disjoint calibration set and reports the
calibration improvement (ECE/MCE/Brier before and after) along with reliability
bins, returning a versioned ``CalibrationResult`` plus the fitted scaler so the
orchestrator can apply it to the (separate) test logits.
"""

from __future__ import annotations

import numpy as np

from .._math import softmax, reliability_bins, brier
from ..schemas import CalibrationResult
from .temperature import TemperatureScaler


class CalibrationPipeline:
    def __init__(self, n_bins: int = 15):
        self.n_bins = n_bins

    def calibrate(self, calib_logits: np.ndarray, calib_labels: np.ndarray) -> tuple[CalibrationResult, TemperatureScaler]:
        calib_logits = np.asarray(calib_logits, dtype=np.float64)
        calib_labels = np.asarray(calib_labels, dtype=int)

        pre_probs = softmax(calib_logits)
        scaler = TemperatureScaler().fit(calib_logits, calib_labels)
        post_probs = scaler.transform(calib_logits)

        pre_ece, pre_mce, pre_bins = reliability_bins(pre_probs, calib_labels, self.n_bins)
        post_ece, post_mce, post_bins = reliability_bins(post_probs, calib_labels, self.n_bins)

        result = CalibrationResult(
            method="temperature_scaling",
            temperature=scaler.temperature,
            pre_ece=pre_ece, post_ece=post_ece,
            pre_mce=pre_mce, post_mce=post_mce,
            pre_brier=brier(pre_probs, calib_labels),
            post_brier=brier(post_probs, calib_labels),
            n_bins=self.n_bins,
            pre_bins=pre_bins, post_bins=post_bins,
            n_calibration=int(calib_labels.size),
        )
        return result, scaler
