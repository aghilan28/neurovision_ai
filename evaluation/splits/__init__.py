"""``evaluation.splits`` — leakage-safe split generation (V1-P4).

Generates **patient-disjoint splits by construction** (AP-2, NR-3): partitioning
happens at the *patient* level and records inherit their patient's assignment, so a
patient can never span two partitions. Generation is **deterministic** (seeded via
:func:`evaluation._canonical.derive_seed`) and **reproducible**: the same patients +
base seed + version always produce the same split, and the split records its inputs.

Implemented:
* Train / validation / test patient-disjoint split.
* Leave-One-Subject-Out (LOSO) folds.

Documented extension points (not built — NR-13): cross-dataset splits and temporal
splits (see ``evaluation/docs``).
"""

from __future__ import annotations

from evaluation.splits.generator import (
    SplitError,
    leave_one_subject_out,
    patient_disjoint_split,
)
from evaluation.splits.schemas import (
    SPLIT_GENERATOR_VERSION,
    Partition,
    SplitResult,
    SplitSpec,
)

__all__ = [
    "SPLIT_GENERATOR_VERSION",
    "Partition",
    "SplitError",
    "SplitResult",
    "SplitSpec",
    "leave_one_subject_out",
    "patient_disjoint_split",
]
