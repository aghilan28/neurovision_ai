"""``evaluation.framework`` — the evaluation orchestrator (V1-P4).

Ties the foundation together into one gated, auditable run:

    split → **leakage gate** → metrics → benchmark (provenance-bound) → lineage →
    audit → registry

**No evaluation proceeds if leakage exists** (AP-2, NR-3): if the split is not
approved, no metrics are computed and no benchmark is recorded. Predictions are
supplied by the caller (a stand-in for future model outputs) — the framework
computes *truth*, it does not train or run models (NR-13).
"""

from __future__ import annotations

from evaluation.framework.runner import Predictions, run_evaluation
from evaluation.framework.schemas import EvaluationRun

__all__ = ["EvaluationRun", "Predictions", "run_evaluation"]
