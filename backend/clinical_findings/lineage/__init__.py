"""``backend/clinical_findings/lineage`` — finding lineage (V2-P3).

Builds content-addressed lineage nodes for findings/evidence/interpretations on
``ml.lineage``, parented to the Review/Case/Study/Inference nodes (shared tracker),
so a finding is fully traceable: Patient → Case → Study → Review → Inference →
Evidence → Finding → Interpretation.
"""

from __future__ import annotations

from .lineage import (
    finding_version_bundle,
    make_finding_lineage,
    make_evidence_lineage,
    make_interpretation_lineage,
)
from ml.lineage import make_lineage_record, LineageRecord  # allowed: backend -> ml

__all__ = ["finding_version_bundle", "make_finding_lineage", "make_evidence_lineage",
           "make_interpretation_lineage", "make_lineage_record", "LineageRecord"]
