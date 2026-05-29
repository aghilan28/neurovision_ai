"""``ml/uncertainty/calibration`` — calibration framework (V1-P6).

Deterministic temperature scaling + reliability analysis (ECE, MCE, Brier,
reliability curves). The pipeline fits a single scalar temperature on a
patient-disjoint calibration set and reports the calibration improvement, so the
confidence the platform reports is honest, not a raw softmax score.
"""

from __future__ import annotations

from .temperature import TemperatureScaler
from .pipeline import CalibrationPipeline

__all__ = ["TemperatureScaler", "CalibrationPipeline"]
