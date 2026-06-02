"""``backend/clinical_cases/lineage`` — case lineage (V2-P1).

Builds content-addressed lineage nodes for Patient → Case → Study on top of the V1
``ml.lineage`` machinery (NR-6: reuse, don't re-implement), and reuses the V1
``LineageTracker`` so clinical nodes and V1 inference nodes live in one graph —
giving Patient → Case → Study → Inference → Artifacts complete traceability.
"""

from __future__ import annotations

from .lineage import (
    clinical_version_bundle,
    make_patient_lineage,
    make_case_lineage,
    make_study_lineage,
)

# re-export the V1 lineage tracker + record type (integration with V1 lineage system)
from ml.lineage import LineageTracker, LineageRecord, make_lineage_record  # allowed: backend -> ml

__all__ = [
    "clinical_version_bundle",
    "make_patient_lineage",
    "make_case_lineage",
    "make_study_lineage",
    "LineageTracker",
    "LineageRecord",
    "make_lineage_record",
]
