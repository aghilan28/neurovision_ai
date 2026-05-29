"""Typed, versioned output contracts for the offline inference platform.

Contracts: Prediction · Probability · Calibration · Conformal · Coverage · Risk ·
Clinical · Summary · Report · Artifact.

Each is a frozen dataclass that validates on construction and exposes a canonical
``to_dict``. Arrays are serialized as plain lists so the on-disk JSON is
deterministic and reproducible. The **Clinical** output is the per-window,
human-meaningful record that fuses class + calibrated confidence + conformal set +
risk/abstain — a clinical output is only valid with its uncertainty attached (NR-4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ..version import OUTPUT_CONTRACT_VERSION


def _as_list(x) -> list:
    if isinstance(x, np.ndarray):
        return x.tolist()
    return list(x)


@dataclass(frozen=True)
class PredictionOutput:
    """Argmax class decisions for the inference set."""

    class_indices: np.ndarray
    class_names: tuple[str, ...]
    patient_ids: Optional[np.ndarray] = None
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        ci = np.asarray(self.class_indices)
        if ci.ndim != 1:
            raise ValueError("class_indices must be 1-D")
        if ci.size and (int(ci.min()) < 0 or int(ci.max()) >= len(self.class_names)):
            raise ValueError("class index out of range")

    def to_dict(self) -> dict:
        ci = np.asarray(self.class_indices, dtype=int)
        return {
            "contract": "PredictionOutput",
            "output_contract_version": self.output_contract_version,
            "n": int(ci.size),
            "class_names": list(self.class_names),
            "class_indices": _as_list(ci),
            "labels": [self.class_names[int(i)] for i in ci],
            "patient_ids": _as_list(self.patient_ids) if self.patient_ids is not None else None,
        }


@dataclass(frozen=True)
class ProbabilityOutput:
    """Calibrated (or raw) class-probability matrix; rows sum to 1."""

    probabilities: np.ndarray
    class_names: tuple[str, ...]
    calibrated: bool = True
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        p = np.asarray(self.probabilities, dtype=float)
        if p.ndim != 2 or p.shape[1] != len(self.class_names):
            raise ValueError("probabilities must be (N, K) matching class_names")
        if not np.allclose(p.sum(axis=1), 1.0, atol=1e-4):
            raise ValueError("probability rows must sum to 1")

    def to_dict(self) -> dict:
        p = np.asarray(self.probabilities, dtype=float)
        return {
            "contract": "ProbabilityOutput",
            "output_contract_version": self.output_contract_version,
            "calibrated": self.calibrated,
            "shape": [int(p.shape[0]), int(p.shape[1])],
            "class_names": list(self.class_names),
            "probabilities": [[round(float(v), 6) for v in row] for row in p],
        }


@dataclass(frozen=True)
class CalibrationOutput:
    """Calibration summary (temperature + ECE/MCE/Brier + reliability bins)."""

    method: str
    temperature: float
    ece_pre: float
    ece_post: float
    mce_post: float
    brier_post: float
    reliability_bins: list
    calibration_version: str
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def to_dict(self) -> dict:
        return {
            "contract": "CalibrationOutput",
            "output_contract_version": self.output_contract_version,
            "calibration_version": self.calibration_version,
            "method": self.method,
            "temperature": round(float(self.temperature), 6),
            "ece": {"pre": round(float(self.ece_pre), 6), "post": round(float(self.ece_post), 6)},
            "mce_post": round(float(self.mce_post), 6),
            "brier_post": round(float(self.brier_post), 6),
            "reliability_bins": self.reliability_bins,
        }


@dataclass(frozen=True)
class ConformalOutput:
    """Conformal prediction sets for the inference set."""

    prediction_sets: np.ndarray  # (N, K) bool
    class_names: tuple[str, ...]
    alpha: float
    target_coverage: float
    qhat: float
    conformal_version: str
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        s = np.asarray(self.prediction_sets)
        if s.ndim != 2 or s.shape[1] != len(self.class_names):
            raise ValueError("prediction_sets must be (N, K) matching class_names")

    def set_sizes(self) -> np.ndarray:
        return np.asarray(self.prediction_sets, dtype=bool).sum(axis=1).astype(int)

    def to_dict(self) -> dict:
        s = np.asarray(self.prediction_sets, dtype=bool)
        sizes = self.set_sizes()
        sets_as_classes = [[self.class_names[k] for k in np.nonzero(row)[0]] for row in s]
        return {
            "contract": "ConformalOutput",
            "output_contract_version": self.output_contract_version,
            "conformal_version": self.conformal_version,
            "alpha": round(float(self.alpha), 6),
            "target_coverage": round(float(self.target_coverage), 6),
            "qhat": round(float(self.qhat), 6),
            "shape": [int(s.shape[0]), int(s.shape[1])],
            "mean_set_size": round(float(sizes.mean()), 6) if sizes.size else 0.0,
            "class_names": list(self.class_names),
            "prediction_sets": sets_as_classes,
        }


@dataclass(frozen=True)
class CoverageOutput:
    """Coverage validation result for the inference set."""

    target_coverage: float
    observed_coverage: float
    coverage_drift: float
    n_violations: int
    violation_rate: float
    average_set_size: float
    per_class_coverage: dict
    reliable: bool
    coverage_version: str
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def to_dict(self) -> dict:
        return {
            "contract": "CoverageOutput",
            "output_contract_version": self.output_contract_version,
            "coverage_version": self.coverage_version,
            "target_coverage": round(float(self.target_coverage), 6),
            "observed_coverage": round(float(self.observed_coverage), 6),
            "coverage_drift": round(float(self.coverage_drift), 6),
            "n_violations": int(self.n_violations),
            "violation_rate": round(float(self.violation_rate), 6),
            "average_set_size": round(float(self.average_set_size), 6),
            "per_class_coverage": self.per_class_coverage,
            "reliable": bool(self.reliable),
        }


@dataclass(frozen=True)
class RiskOutput:
    """Per-window risk scores, bands, and abstain/escalate decisions."""

    risk_scores: np.ndarray
    confidence: np.ndarray
    bands: np.ndarray
    abstain: np.ndarray
    band_thresholds: dict
    abstain_rate: float
    per_class_risk: dict
    risk_version: str
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def to_dict(self) -> dict:
        bands = np.asarray(self.bands)
        unique, counts = np.unique(bands, return_counts=True)
        return {
            "contract": "RiskOutput",
            "output_contract_version": self.output_contract_version,
            "risk_version": self.risk_version,
            "n": int(np.asarray(self.risk_scores).size),
            "band_thresholds": self.band_thresholds,
            "band_counts": {str(u): int(c) for u, c in zip(unique, counts)},
            "abstain_rate": round(float(self.abstain_rate), 6),
            "n_abstain": int(np.asarray(self.abstain, dtype=bool).sum()),
            "risk_scores": [round(float(v), 6) for v in _as_list(self.risk_scores)],
            "confidence": [round(float(v), 6) for v in _as_list(self.confidence)],
            "abstain": [bool(v) for v in _as_list(self.abstain)],
            "per_class_risk": self.per_class_risk,
        }


@dataclass(frozen=True)
class ClinicalOutput:
    """Per-window fused clinical record (class + confidence + set + risk + abstain).

    A clinical output is only valid because each window carries its calibrated
    uncertainty and conformal set (NR-4): never a bare label.
    """

    records: list  # list of per-window dicts
    class_names: tuple[str, ...]
    n_abstain: int
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    @property
    def n(self) -> int:
        return len(self.records)

    def to_dict(self) -> dict:
        return {
            "contract": "ClinicalOutput",
            "output_contract_version": self.output_contract_version,
            "n": self.n,
            "n_abstain": int(self.n_abstain),
            "class_names": list(self.class_names),
            "records": self.records,
        }

    @staticmethod
    def build(*, class_indices, calibrated_probs, prediction_sets, risk_scores,
              risk_bands, abstain, class_names, patient_ids=None) -> "ClinicalOutput":
        ci = np.asarray(class_indices, dtype=int)
        probs = np.asarray(calibrated_probs, dtype=float)
        sets = np.asarray(prediction_sets, dtype=bool)
        risk = np.asarray(risk_scores, dtype=float)
        bands = np.asarray(risk_bands)
        ab = np.asarray(abstain, dtype=bool)
        records = []
        for i in range(ci.size):
            records.append({
                "window_index": int(i),
                "patient_id": int(patient_ids[i]) if patient_ids is not None else None,
                "predicted_class": class_names[int(ci[i])],
                "calibrated_confidence": round(float(probs[i].max()), 6),
                "conformal_set": [class_names[k] for k in np.nonzero(sets[i])[0]],
                "set_size": int(sets[i].sum()),
                "risk_score": round(float(risk[i]), 6),
                "risk_band": str(bands[i]),
                "abstain": bool(ab[i]),
            })
        return ClinicalOutput(records=records, class_names=tuple(class_names),
                              n_abstain=int(ab.sum()))


@dataclass(frozen=True)
class SummaryOutput:
    """Headline summary fusing metrics + calibration + coverage + risk + versions."""

    model_name: str
    headline: dict
    version_bundle: dict
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def to_dict(self) -> dict:
        return {
            "contract": "SummaryOutput",
            "output_contract_version": self.output_contract_version,
            "model_name": self.model_name,
            "headline": self.headline,
            "version_bundle": self.version_bundle,
        }


@dataclass(frozen=True)
class ReportOutput:
    """References to the registered reports produced for an inference."""

    reports: dict  # name -> artifact ref dict
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def to_dict(self) -> dict:
        return {
            "contract": "ReportOutput",
            "output_contract_version": self.output_contract_version,
            "reports": self.reports,
        }


@dataclass(frozen=True)
class ArtifactOutput:
    """References + checksums for every artifact persisted for an inference."""

    artifacts: dict  # name -> {relpath, checksum, ...}
    output_contract_version: str = OUTPUT_CONTRACT_VERSION

    def to_dict(self) -> dict:
        return {
            "contract": "ArtifactOutput",
            "output_contract_version": self.output_contract_version,
            "n_artifacts": len(self.artifacts),
            "artifacts": self.artifacts,
        }
