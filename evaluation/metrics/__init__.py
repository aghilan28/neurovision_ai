"""``evaluation.metrics`` — deterministic metrics framework (V1-P4).

Pure-NumPy classification and ranking metrics (no third-party ML library), each
with **metadata** (version, kind, inputs, output range) registered in a
:class:`~evaluation.metrics.registry.MetricRegistry`, and each result carrying a
provenance fingerprint of its inputs (metric **lineage**).

Calibration and clinical metrics are registered as **placeholders** only — their
computation is owned by the future uncertainty/clinical phases and is intentionally
not implemented here (NR-13).
"""

from __future__ import annotations

from evaluation.metrics.classification import (
    accuracy,
    balanced_accuracy,
    confusion_matrix,
    f1_score,
    precision_recall,
    sensitivity_specificity,
)
from evaluation.metrics.ranking import auprc, auroc
from evaluation.metrics.registry import (
    METRICS_VERSION,
    MetricRegistry,
    default_metric_registry,
)
from evaluation.metrics.schemas import MetricDefinition, MetricKind, MetricResult

__all__ = [
    "METRICS_VERSION",
    "MetricDefinition",
    "MetricKind",
    "MetricRegistry",
    "MetricResult",
    "accuracy",
    "auprc",
    "auroc",
    "balanced_accuracy",
    "confusion_matrix",
    "default_metric_registry",
    "f1_score",
    "precision_recall",
    "sensitivity_specificity",
]
