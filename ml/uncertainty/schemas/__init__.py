"""``ml/uncertainty/schemas`` — typed, versioned uncertainty contracts (V1-P6).

Result contracts for each uncertainty stage. Every contract is versioned and
exposes a compact, canonical ``to_dict`` so reports are reproducible and auditable,
and so the clinical confidence layer is never a black box (the V1-P6 principle:
no black-box confidence scores).
"""

from __future__ import annotations

from .contracts import (
    CalibrationResult,
    ConformalResult,
    CoverageResult,
    RiskResult,
    ReliabilityArtifacts,
)

__all__ = [
    "CalibrationResult",
    "ConformalResult",
    "CoverageResult",
    "RiskResult",
    "ReliabilityArtifacts",
]
