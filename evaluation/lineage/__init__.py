"""``evaluation.lineage`` — end-to-end evaluation provenance (V1-P4).

Captures the full chain behind every metric: dataset (+version) → split (+generator
version) → preprocessing version → evaluation version → (future model version) →
result artifacts, plus the per-metric input fingerprints. Makes **every metric
traceable** (AP-5, NR-11).
"""

from __future__ import annotations

from evaluation.lineage.tracker import (
    LINEAGE_VERSION,
    EvaluationLineage,
    build_evaluation_lineage,
)

__all__ = ["LINEAGE_VERSION", "EvaluationLineage", "build_evaluation_lineage"]
