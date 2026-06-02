"""Typed, versioned model I/O contracts (V1-P5).

Contracts
---------
* ``InputWindow``           — a single preprocessed EEG window + provenance.
* ``InputBatch``            — a batch of windows + patient ids + provenance.
* ``ProbabilityOutput``     — calibrated/raw class-probability matrix.
* ``ClassOutput``           — argmax class decisions.
* ``MetadataOutput``        — the provenance bundle attached to every prediction.
* ``UncertaintyPlaceholder``— the typed slot the uncertainty layer (V1-P6) fills.
* ``ConformalOutput``       — conformal prediction sets (future/forward contract).
* ``Prediction``            — the unified inference result tying them together.

Every contract:
  * validates its own shape/semantics on construction (fail fast),
  * carries ``CONTRACT_VERSION`` (governance / reproducibility),
  * exposes ``to_dict`` for canonical, hashable serialization.

A clinical ``Prediction`` is only *complete* once its uncertainty placeholder has
been filled by the uncertainty layer — bare labels are never a valid clinical
output (NR-4). The placeholder makes that requirement explicit and checkable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

from ..version import CONTRACT_VERSION

__all__ = [
    "CONTRACT_VERSION",
    "InputWindow",
    "InputBatch",
    "ProbabilityOutput",
    "ClassOutput",
    "MetadataOutput",
    "UncertaintyPlaceholder",
    "ConformalOutput",
    "Prediction",
]


@dataclass(frozen=True)
class InputWindow:
    """A single preprocessed EEG window with provenance."""

    signal: np.ndarray  # (C, T) float
    patient_id: object
    preprocessing_version: str
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.signal.ndim != 2:
            raise ValueError("InputWindow.signal must be 2-D (C, T)")

    @property
    def n_channels(self) -> int:
        return int(self.signal.shape[0])

    @property
    def n_samples(self) -> int:
        return int(self.signal.shape[1])

    def to_dict(self) -> dict:
        return {
            "contract": "InputWindow",
            "contract_version": self.contract_version,
            "shape": [self.n_channels, self.n_samples],
            "patient_id": self.patient_id,
            "preprocessing_version": self.preprocessing_version,
        }


@dataclass(frozen=True)
class InputBatch:
    """A batch of preprocessed EEG windows with patient ids + provenance."""

    signals: np.ndarray  # (N, C, T) float
    patient_ids: np.ndarray  # (N,)
    preprocessing_version: str
    dataset_version: Optional[str] = None
    split_version: Optional[str] = None
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.signals.ndim != 3:
            raise ValueError("InputBatch.signals must be 3-D (N, C, T)")
        if self.patient_ids.shape[0] != self.signals.shape[0]:
            raise ValueError("patient_ids length must equal batch size")

    @property
    def n(self) -> int:
        return int(self.signals.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.signals.shape[1])

    @property
    def n_samples(self) -> int:
        return int(self.signals.shape[2])

    def to_dict(self) -> dict:
        return {
            "contract": "InputBatch",
            "contract_version": self.contract_version,
            "shape": [self.n, self.n_channels, self.n_samples],
            "n_patients": int(np.unique(self.patient_ids).size),
            "preprocessing_version": self.preprocessing_version,
            "dataset_version": self.dataset_version,
            "split_version": self.split_version,
        }


@dataclass(frozen=True)
class ProbabilityOutput:
    """Per-window class-probability matrix (rows sum to 1)."""

    probabilities: np.ndarray  # (N, K)
    class_names: tuple[str, ...]
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        p = self.probabilities
        if p.ndim != 2:
            raise ValueError("probabilities must be 2-D (N, K)")
        if p.shape[1] != len(self.class_names):
            raise ValueError("probabilities width must equal len(class_names)")
        if np.any(p < -1e-6) or np.any(p > 1.0 + 1e-6):
            raise ValueError("probabilities must lie in [0, 1]")
        row_sums = p.sum(axis=1)
        if not np.allclose(row_sums, 1.0, atol=1e-4):
            raise ValueError("probability rows must sum to 1")

    @property
    def n(self) -> int:
        return int(self.probabilities.shape[0])

    @property
    def n_classes(self) -> int:
        return int(self.probabilities.shape[1])

    def confidence(self) -> np.ndarray:
        """Top-1 probability per window (the model's stated confidence)."""
        return self.probabilities.max(axis=1)

    def to_dict(self) -> dict:
        return {
            "contract": "ProbabilityOutput",
            "contract_version": self.contract_version,
            "shape": [self.n, self.n_classes],
            "class_names": list(self.class_names),
        }


@dataclass(frozen=True)
class ClassOutput:
    """Argmax class decisions."""

    class_indices: np.ndarray  # (N,) int
    class_names: tuple[str, ...]
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.class_indices.ndim != 1:
            raise ValueError("class_indices must be 1-D")
        if self.class_indices.size and (
            int(self.class_indices.min()) < 0
            or int(self.class_indices.max()) >= len(self.class_names)
        ):
            raise ValueError("class_indices out of range for class_names")

    def labels(self) -> list[str]:
        return [self.class_names[int(i)] for i in self.class_indices]

    def to_dict(self) -> dict:
        return {
            "contract": "ClassOutput",
            "contract_version": self.contract_version,
            "n": int(self.class_indices.size),
            "class_names": list(self.class_names),
        }


@dataclass(frozen=True)
class MetadataOutput:
    """The provenance bundle attached to every prediction (AP-5 / NR-11).

    Makes a prediction traceable to the exact data, preprocessing, split, model,
    and lineage that produced it.
    """

    model_name: str
    model_version: str
    architecture_version: str
    preprocessing_version: str
    dataset_version: Optional[str] = None
    split_version: Optional[str] = None
    training_version: Optional[str] = None
    lineage_id: Optional[str] = None
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> dict:
        return {
            "contract": "MetadataOutput",
            "contract_version": self.contract_version,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "architecture_version": self.architecture_version,
            "preprocessing_version": self.preprocessing_version,
            "dataset_version": self.dataset_version,
            "split_version": self.split_version,
            "training_version": self.training_version,
            "lineage_id": self.lineage_id,
        }


@dataclass(frozen=True)
class UncertaintyPlaceholder:
    """The typed slot the uncertainty layer (V1-P6) fills.

    For a freshly-trained baseline, ``calibrated`` is False: the model emits raw
    confidence but it has not yet been calibrated/conformalized. The clinical
    completeness rule (NR-4) requires this to be filled before an output is
    treated as a clinical output. ``is_calibrated`` makes that checkable.
    """

    calibrated: bool = False
    calibration_version: Optional[str] = None
    conformal_version: Optional[str] = None
    confidence: Optional[np.ndarray] = None  # (N,) top-1 probability or calibrated score
    risk_score: Optional[np.ndarray] = None  # (N,) in [0,1]; filled by risk framework
    abstain: Optional[np.ndarray] = None     # (N,) bool; True => escalate to human
    notes: str = "uncalibrated baseline output; to be filled by ml/uncertainty (V1-P6)"
    contract_version: str = CONTRACT_VERSION

    def is_calibrated(self) -> bool:
        return bool(self.calibrated)

    def to_dict(self) -> dict:
        return {
            "contract": "UncertaintyPlaceholder",
            "contract_version": self.contract_version,
            "calibrated": self.calibrated,
            "calibration_version": self.calibration_version,
            "conformal_version": self.conformal_version,
            "has_confidence": self.confidence is not None,
            "has_risk_score": self.risk_score is not None,
            "has_abstain": self.abstain is not None,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ConformalOutput:
    """Conformal prediction sets (forward contract, produced by V1-P6).

    ``prediction_sets`` is an (N, K) boolean membership matrix: entry (i, k) is
    True iff class k is included in the conformal set for window i.
    """

    prediction_sets: np.ndarray  # (N, K) bool
    target_coverage: float
    class_names: tuple[str, ...]
    conformal_version: str
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        s = self.prediction_sets
        if s.ndim != 2 or s.shape[1] != len(self.class_names):
            raise ValueError("prediction_sets must be (N, K) matching class_names")
        if not (0.0 < self.target_coverage < 1.0):
            raise ValueError("target_coverage must be in (0, 1)")

    def set_sizes(self) -> np.ndarray:
        return self.prediction_sets.sum(axis=1).astype(int)

    def to_dict(self) -> dict:
        sizes = self.set_sizes()
        return {
            "contract": "ConformalOutput",
            "contract_version": self.contract_version,
            "conformal_version": self.conformal_version,
            "target_coverage": self.target_coverage,
            "shape": list(self.prediction_sets.shape),
            "mean_set_size": float(sizes.mean()) if sizes.size else 0.0,
            "class_names": list(self.class_names),
        }


@dataclass(frozen=True)
class Prediction:
    """Unified inference result: classes + probabilities + provenance + uncertainty.

    A ``Prediction`` is a *clinical output* only when ``uncertainty.is_calibrated``
    is True (NR-4). ``is_clinically_complete`` exposes that gate for governance.
    """

    probability: ProbabilityOutput
    classification: ClassOutput
    metadata: MetadataOutput
    uncertainty: UncertaintyPlaceholder = field(default_factory=UncertaintyPlaceholder)
    conformal: Optional[ConformalOutput] = None
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.probability.n != self.classification.class_indices.size:
            raise ValueError("probability and classification batch sizes differ")

    @property
    def n(self) -> int:
        return self.probability.n

    def is_clinically_complete(self) -> bool:
        """True iff calibrated uncertainty is attached (the NR-4 gate)."""
        return self.uncertainty.is_calibrated()

    def to_dict(self) -> dict:
        return {
            "contract": "Prediction",
            "contract_version": self.contract_version,
            "n": self.n,
            "clinically_complete": self.is_clinically_complete(),
            "probability": self.probability.to_dict(),
            "classification": self.classification.to_dict(),
            "metadata": self.metadata.to_dict(),
            "uncertainty": self.uncertainty.to_dict(),
            "conformal": self.conformal.to_dict() if self.conformal is not None else None,
        }
