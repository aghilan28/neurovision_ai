"""``backend/offline_inference/schemas`` — typed, versioned output contracts (V1-P7).

Every value the platform emits is a typed, versioned contract with a canonical,
JSON-able ``to_dict``. These are what get registered as artifacts and what the
research application (V1-P8) reads — never recomputing anything (presentation only).
"""

from __future__ import annotations

from .outputs import (
    OUTPUT_CONTRACT_VERSION,
    PredictionOutput,
    ProbabilityOutput,
    CalibrationOutput,
    ConformalOutput,
    CoverageOutput,
    RiskOutput,
    ClinicalOutput,
    SummaryOutput,
    ReportOutput,
    ArtifactOutput,
)

__all__ = [
    "OUTPUT_CONTRACT_VERSION",
    "PredictionOutput",
    "ProbabilityOutput",
    "CalibrationOutput",
    "ConformalOutput",
    "CoverageOutput",
    "RiskOutput",
    "ClinicalOutput",
    "SummaryOutput",
    "ReportOutput",
    "ArtifactOutput",
]
