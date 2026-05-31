"""``backend/dataset_integration/audit`` — immutable dataset audit log (DRP1-I).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel audit
system) bound to :class:`DatasetAuditRecord`. Every inventory/registration/validation/
governance/readiness event is appended immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import DatasetAuditRecord


def make_dataset_audit_log() -> ImmutableAuditLog:
    return ImmutableAuditLog(record_cls=DatasetAuditRecord)


__all__ = ["make_dataset_audit_log", "ImmutableAuditLog", "AuditError"]
