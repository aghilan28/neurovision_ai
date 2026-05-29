"""Typed, versioned result contracts for the uncertainty layer (V1-P6).

These wrap the (sometimes large) numpy arrays produced by each stage and expose
compact ``to_dict`` summaries for reproducible reports. Full arrays remain
available as attributes for in-memory chaining (calibration -> conformal ->
coverage -> risk).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ..version import (
    CALIBRATION_VERSION,
    CONFORMAL_VERSION,
    COVERAGE_VERSION,
    RISK_VERSION,
    RELIABILITY_VERSION,
)


@dataclass(frozen=True)
class CalibrationResult:
    """Outcome of fitting + measuring calibration (e.g. temperature scaling)."""

    method: str
    temperature: float
    pre_ece: float
    post_ece: float
    pre_mce: float
    post_mce: float
    pre_brier: float
    post_brier: float
    n_bins: int
    pre_bins: list
    post_bins: list
    n_calibration: int
    calibration_version: str = CALIBRATION_VERSION

    def improved(self) -> bool:
        return self.post_ece <= self.pre_ece + 1e-9

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "calibration_version": self.calibration_version,
            "temperature": round(self.temperature, 6),
            "n_calibration": self.n_calibration,
            "n_bins": self.n_bins,
            "ece": {"pre": round(self.pre_ece, 6), "post": round(self.post_ece, 6)},
            "mce": {"pre": round(self.pre_mce, 6), "post": round(self.post_mce, 6)},
            "brier": {"pre": round(self.pre_brier, 6), "post": round(self.post_brier, 6)},
            "improved": self.improved(),
            "reliability_pre": self.pre_bins,
            "reliability_post": self.post_bins,
        }


@dataclass(frozen=True)
class ConformalResult:
    """Outcome of split-conformal calibration + prediction-set construction."""

    method: str
    alpha: float
    target_coverage: float
    qhat: float
    prediction_sets: np.ndarray  # (N, K) bool
    class_names: tuple[str, ...]
    n_calibration: int
    conformal_version: str = CONFORMAL_VERSION

    def set_sizes(self) -> np.ndarray:
        return self.prediction_sets.sum(axis=1).astype(int)

    def to_dict(self) -> dict:
        sizes = self.set_sizes()
        size_hist = {int(s): int(c) for s, c in zip(*np.unique(sizes, return_counts=True))}
        return {
            "method": self.method,
            "conformal_version": self.conformal_version,
            "alpha": round(self.alpha, 6),
            "target_coverage": round(self.target_coverage, 6),
            "qhat": round(float(self.qhat), 6),
            "n_calibration": self.n_calibration,
            "n_predicted": int(self.prediction_sets.shape[0]),
            "mean_set_size": round(float(sizes.mean()), 6) if sizes.size else 0.0,
            "set_size_histogram": size_hist,
            "empty_set_rate": round(float(np.mean(sizes == 0)), 6) if sizes.size else 0.0,
            "class_names": list(self.class_names),
        }


@dataclass(frozen=True)
class CoverageResult:
    """Coverage tracking: target vs observed, drift, violations, audit."""

    target_coverage: float
    observed_coverage: float
    coverage_drift: float
    n_violations: int
    violation_rate: float
    per_class_coverage: dict
    average_set_size: float
    reliable: bool
    audit: dict
    coverage_version: str = COVERAGE_VERSION

    def to_dict(self) -> dict:
        return {
            "coverage_version": self.coverage_version,
            "target_coverage": round(self.target_coverage, 6),
            "observed_coverage": round(self.observed_coverage, 6),
            "coverage_drift": round(self.coverage_drift, 6),
            "n_violations": self.n_violations,
            "violation_rate": round(self.violation_rate, 6),
            "average_set_size": round(self.average_set_size, 6),
            "per_class_coverage": self.per_class_coverage,
            "reliable": self.reliable,
            "audit": self.audit,
        }


@dataclass(frozen=True)
class RiskResult:
    """Per-window clinical risk scores, confidence bands, and abstain decisions."""

    risk_scores: np.ndarray   # (N,) in [0,1]
    confidence: np.ndarray    # (N,) calibrated top-1 probability
    bands: np.ndarray         # (N,) band labels: "low"/"medium"/"high" risk
    abstain: np.ndarray       # (N,) bool: True => escalate to human
    low_confidence_alerts: np.ndarray  # indices flagged for review
    band_thresholds: dict
    per_class_risk: dict
    abstain_rate: float
    risk_version: str = RISK_VERSION

    def to_dict(self) -> dict:
        unique, counts = np.unique(self.bands, return_counts=True)
        band_counts = {str(u): int(c) for u, c in zip(unique, counts)}
        return {
            "risk_version": self.risk_version,
            "n": int(self.risk_scores.size),
            "band_thresholds": self.band_thresholds,
            "band_counts": band_counts,
            "abstain_rate": round(float(self.abstain_rate), 6),
            "n_low_confidence_alerts": int(self.low_confidence_alerts.size),
            "mean_risk": round(float(self.risk_scores.mean()), 6) if self.risk_scores.size else 0.0,
            "mean_confidence": round(float(self.confidence.mean()), 6) if self.confidence.size else 0.0,
            "per_class_risk": self.per_class_risk,
        }


@dataclass(frozen=True)
class ReliabilityArtifacts:
    """Reliability analysis artifacts (diagrams/tables/histograms/profiles as data)."""

    reliability_diagram: list      # bins of (confidence, accuracy, count)
    calibration_table: list        # tabular rows
    confidence_histogram: dict      # histogram of top-1 confidence
    prediction_confidence_profiles: dict  # per-class mean confidence
    risk_profiles: dict             # distribution of risk per band/class
    reliability_version: str = RELIABILITY_VERSION

    def to_dict(self) -> dict:
        return {
            "reliability_version": self.reliability_version,
            "reliability_diagram": self.reliability_diagram,
            "calibration_table": self.calibration_table,
            "confidence_histogram": self.confidence_histogram,
            "prediction_confidence_profiles": self.prediction_confidence_profiles,
            "risk_profiles": self.risk_profiles,
        }
