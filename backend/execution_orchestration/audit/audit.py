"""Execution audit log = the shared ImmutableAuditLog bound to ExecutionAuditRecord.

No parallel audit system: the execution subsystem reuses the platform's single
hash-chained :class:`ImmutableAuditLog` implementation (V2-P1), parameterised with
:class:`ExecutionAuditRecord`. Every creation/authorization/activation/pause/block/
completion/termination and version change is appended immutably.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import ExecutionAuditRecord


def make_execution_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained execution audit log."""
    return ImmutableAuditLog(record_cls=ExecutionAuditRecord)


__all__ = ["make_execution_audit_log", "ImmutableAuditLog", "AuditError"]
