"""``ml/uncertainty`` — Uncertainty & Calibration Layer (V1-P6).

The clinical confidence layer. It answers not only "what is the prediction?" but
"how confident should we be?" — with calibrated, conformal, coverage-validated,
risk-scored uncertainty that is versioned, traceable, reproducible, auditable, and
clinically explainable (no black-box confidence scores).

Subsystems: calibration · conformal · coverage · reliability · risk · validation ·
registry · lineage · reports · schemas. The ``UncertaintyPipeline`` chains them
into one deterministic flow.

Boundary: part of the ML layer; imports only ``ml`` submodules + foundations.
Never imports ``evaluation`` (NR-8) — the evaluation layer independently verifies
calibration/coverage and is wired in by the orchestrator (``scripts/``).
"""

from __future__ import annotations

from .version import (
    UNCERTAINTY_LAYER_VERSION,
    CALIBRATION_VERSION,
    CONFORMAL_VERSION,
    COVERAGE_VERSION,
    RISK_VERSION,
    RELIABILITY_VERSION,
    UNCERTAINTY_REGISTRY_VERSION,
)
from .schemas import (
    CalibrationResult,
    ConformalResult,
    CoverageResult,
    RiskResult,
    ReliabilityArtifacts,
)
from .calibration import CalibrationPipeline, TemperatureScaler
from .conformal import SplitConformalPredictor
from .coverage import CoverageTracker
from .risk import RiskAssessor
from .reliability import ReliabilityAnalyzer
from .registry import UncertaintyRecord, UncertaintyRegistry
from .validation import UncertaintyValidator, UncertaintyValidationError
from .pipeline import UncertaintyPipeline, UncertaintyOutput

__all__ = [
    "UNCERTAINTY_LAYER_VERSION",
    "CALIBRATION_VERSION",
    "CONFORMAL_VERSION",
    "COVERAGE_VERSION",
    "RISK_VERSION",
    "RELIABILITY_VERSION",
    "UNCERTAINTY_REGISTRY_VERSION",
    "CalibrationResult",
    "ConformalResult",
    "CoverageResult",
    "RiskResult",
    "ReliabilityArtifacts",
    "CalibrationPipeline",
    "TemperatureScaler",
    "SplitConformalPredictor",
    "CoverageTracker",
    "RiskAssessor",
    "ReliabilityAnalyzer",
    "UncertaintyRecord",
    "UncertaintyRegistry",
    "UncertaintyValidator",
    "UncertaintyValidationError",
    "UncertaintyPipeline",
    "UncertaintyOutput",
]
