"""``backend/operations_platform/audit`` — immutable operations audit log (T4-G).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel audit
system), bound to :class:`OperationsAuditRecord`. Every health / monitoring / diagnostic /
qualification / readiness event is appended immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import AuditError, ImmutableAuditLog

from ..models.domain import OperationsAuditRecord


def make_operations_audit_log() -> ImmutableAuditLog:
    return ImmutableAuditLog(record_cls=OperationsAuditRecord)


__all__ = ["make_operations_audit_log", "ImmutableAuditLog", "AuditError"]
