"""``ml/uncertainty/conformal`` — split conformal prediction (V1-P6).

Distribution-free prediction sets with a marginal coverage guarantee, calibrated
on a patient-disjoint calibration set. The reference technique for calibrated
uncertainty with guarantees (GLOSSARY → Conformal Prediction).
"""

from __future__ import annotations

from .split_conformal import SplitConformalPredictor

__all__ = ["SplitConformalPredictor"]
