"""``evaluation.registry`` — discoverable registry of evaluation runs (V1-P4).

Tracks every evaluation run with its versions, dataset, split, metrics, results,
artifacts, and dependencies, so any evaluation is **discoverable** and auditable.
JSON-backed and deterministic (canonical serialization).
"""

from __future__ import annotations

from evaluation.registry.registry import (
    EVALUATION_REGISTRY_SCHEMA,
    EvaluationRegistry,
    RegisteredEvaluation,
    RegistryError,
)

__all__ = [
    "EVALUATION_REGISTRY_SCHEMA",
    "EvaluationRegistry",
    "RegisteredEvaluation",
    "RegistryError",
]
