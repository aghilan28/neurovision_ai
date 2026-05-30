"""Task audit log = the shared ImmutableAuditLog bound to TaskAuditRecord.

No parallel audit system: the task subsystem reuses the platform's single
hash-chained :class:`ImmutableAuditLog` implementation (V2-P1), parameterised with
:class:`TaskAuditRecord`. Every creation/modification/approval/readiness/blocking/
completion/archival, dependency change, and version change is appended immutably.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import TaskAuditRecord


def make_task_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained task audit log."""
    return ImmutableAuditLog(record_cls=TaskAuditRecord)


__all__ = ["make_task_audit_log", "ImmutableAuditLog", "AuditError"]
