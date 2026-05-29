"""``frontend/offline_research_app/workflows`` — the five user workflows (V1-P8).

Each workflow builds a ``Page`` view-model from registered artifacts only:
  1. Upload (file metadata / quality / readiness)
  2. Dataset Intelligence (profiles / quality / leakage / readiness)
  3. Inference (prediction / probability / calibration / conformal / coverage / risk)
  4. Benchmark (model benchmarks / evaluation / split / metrics / history)
  5. Audit (lineage / artifacts / registries / versions / decision & validation trail)
"""

from __future__ import annotations

from .workflows import (
    upload_workflow, dataset_intelligence_workflow, inference_workflow,
    benchmark_workflow, audit_workflow, all_workflows,
)

__all__ = [
    "upload_workflow", "dataset_intelligence_workflow", "inference_workflow",
    "benchmark_workflow", "audit_workflow", "all_workflows",
]
