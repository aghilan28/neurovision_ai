"""``backend/dataset_acquisition/audit`` — immutable acquisition audit log (T1-H).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel audit
system), bound to :class:`AcquisitionAuditRecord`. Every acquire / verify / connect /
validate / label / inventory / score / register event is appended immutably and is
tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import AcquisitionAuditRecord


def make_acquisition_audit_log() -> ImmutableAuditLog:
    return ImmutableAuditLog(record_cls=AcquisitionAuditRecord)


__all__ = ["make_acquisition_audit_log", "ImmutableAuditLog", "AuditError"]
