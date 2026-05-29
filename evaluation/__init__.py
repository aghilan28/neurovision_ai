"""``evaluation/`` — Validation Harness (V1-P4 integration surface).

Decides whether a result is real: enforces and audits patient-disjoint evaluation
(AP-2 / NR-3) and measures calibration/coverage (AP-4). Imports ``ml`` (for the
result contract), ``datasets`` and ``preprocessing``; it is never imported by
``ml`` (no cycle).

This is the minimal, focused realization of the evaluation foundation that V1-P5
(benchmarking) and V1-P6 (uncertainty validation) require. See ``evaluation/README.md``.
"""

from __future__ import annotations

from .version import EVALUATION_VERSION
from .metrics import compute_metrics, confusion_matrix
from .calibration_metrics import (
    expected_calibration_error,
    brier_score,
    empirical_coverage,
    average_set_size,
)
from .harness import PatientDisjointEvaluator, verify_patient_disjoint

__all__ = [
    "EVALUATION_VERSION",
    "compute_metrics",
    "confusion_matrix",
    "expected_calibration_error",
    "brier_score",
    "empirical_coverage",
    "average_set_size",
    "PatientDisjointEvaluator",
    "verify_patient_disjoint",
]
