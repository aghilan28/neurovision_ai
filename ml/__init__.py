"""``ml/`` — ML Layer (V1-P5 Baseline Models + V1-P6 Uncertainty & Calibration).

Owns model definitions, training, uncertainty-aware inference, and the governance
substrate (registry, artifacts, lineage, benchmarking) for the baseline models.

Boundary (NR-8): ``ml`` imports ``preprocessing`` and ``datasets`` only. It does
**not** import ``evaluation`` (evaluation imports ml — no cycle). Cross-layer
orchestration that needs both ml and evaluation lives in ``scripts/``.

See ``ml/README.md`` and ``ml/docs/`` for the full contract.
"""

from __future__ import annotations

from .version import (
    ML_LAYER_VERSION,
    ARCHITECTURE_VERSIONS,
    TRAINING_FRAMEWORK_VERSION,
    CONTRACT_VERSION,
    REGISTRY_VERSION,
    ARTIFACT_VERSION,
    LINEAGE_VERSION,
    BENCHMARK_VERSION,
)

__all__ = [
    "ML_LAYER_VERSION",
    "ARCHITECTURE_VERSIONS",
    "TRAINING_FRAMEWORK_VERSION",
    "CONTRACT_VERSION",
    "REGISTRY_VERSION",
    "ARTIFACT_VERSION",
    "LINEAGE_VERSION",
    "BENCHMARK_VERSION",
]
