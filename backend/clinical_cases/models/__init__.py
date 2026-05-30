"""``backend/clinical_cases/models`` — the Case domain model (V2-P1).

First-class clinical domain entities. The **Case** is the primary organizational
object of the platform: a permanent, versioned, auditable, lineage-tracked record
that thinks in terms of Patient → Case → Study (not files/folders).
"""

from __future__ import annotations

from .domain import (
    CaseStatus,
    PatientIdentity,
    CaseIdentity,
    StudyIdentity,
    CaseMetadata,
    CaseState,
    CaseAuditRecord,
    CaseLineageRecord,
    CaseVersion,
    CaseRegistryRecord,
    Case,
)

__all__ = [
    "CaseStatus",
    "PatientIdentity",
    "CaseIdentity",
    "StudyIdentity",
    "CaseMetadata",
    "CaseState",
    "CaseAuditRecord",
    "CaseLineageRecord",
    "CaseVersion",
    "CaseRegistryRecord",
    "Case",
]
