"""``backend/clinical_findings/models`` — the Finding domain model (V2-P3).

A **Finding** is a *structured clinical observation linked to evidence* — never a
prediction, probability, diagnosis, or recommendation. Findings are permanent,
versioned, evidence-linked, case/study/review-linked, lineage-tracked workflow
entities. Interpretations are modelled as a **separate** entity (not merged into
the finding).
"""

from __future__ import annotations

from .domain import (
    FindingStatus,
    FindingIdentity,
    FindingRecord,
    FindingMetadata,
    FindingEvidence,
    FindingInterpretation,
    FindingVersion,
    FindingAuditRecord,
    FindingLineageRecord,
    FindingRegistryRecord,
    Finding,
)

__all__ = [
    "FindingStatus",
    "FindingIdentity",
    "FindingRecord",
    "FindingMetadata",
    "FindingEvidence",
    "FindingInterpretation",
    "FindingVersion",
    "FindingAuditRecord",
    "FindingLineageRecord",
    "FindingRegistryRecord",
    "Finding",
]
