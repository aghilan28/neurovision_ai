"""``backend/application_platform/audit`` — immutable application audit log (T3-J).

Reuses the platform's single tamper-evident :class:`ImmutableAuditLog` (no parallel audit
system), bound to :class:`ApplicationAuditRecord`. Every request / upload / analysis /
prediction / report / readiness event is appended immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import AuditError, ImmutableAuditLog

from ..models.domain import ApplicationAuditRecord


def make_application_audit_log() -> ImmutableAuditLog:
    return ImmutableAuditLog(record_cls=ApplicationAuditRecord)


__all__ = ["make_application_audit_log", "ImmutableAuditLog", "AuditError"]
