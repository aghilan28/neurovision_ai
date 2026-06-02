"""``evaluation.validation`` — the leakage gate + evaluation audits (V1-P4).

The **cardinal guarantee** of the platform: no evaluation may proceed if leakage
exists (AP-2, NR-3). This subpackage detects patient/session/recording overlap and
hidden leakage in a split, validates split correctness, and (with the framework)
audits whole evaluation runs for version/artifact/lineage consistency.
"""

from __future__ import annotations

from evaluation.validation.audit import audit_evaluation
from evaluation.validation.patient_disjoint import (
    LeakageError,
    approve_split,
    detect_leakage,
    require_leakage_free,
    validate_split,
)
from evaluation.validation.schemas import (
    VALIDATION_VERSION,
    ApprovalReport,
    LeakageReport,
    SplitValidationReport,
)

__all__ = [
    "VALIDATION_VERSION",
    "ApprovalReport",
    "LeakageError",
    "LeakageReport",
    "SplitValidationReport",
    "approve_split",
    "audit_evaluation",
    "detect_leakage",
    "require_leakage_free",
    "validate_split",
]
