"""``ml/schemas`` — typed, versioned model contracts (V1-P5).

Every input/output that crosses an ML boundary is a typed, versioned contract.
This makes outputs self-describing and auditable (AP-5 / AP-8) and gives the
uncertainty layer (V1-P6) explicit, contracted slots to fill (NR-4).
"""

from __future__ import annotations

from .contracts import (
    CONTRACT_VERSION,
    InputWindow,
    InputBatch,
    ProbabilityOutput,
    ClassOutput,
    MetadataOutput,
    UncertaintyPlaceholder,
    ConformalOutput,
    Prediction,
)

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
