"""Intelligence audit log = the shared ImmutableAuditLog bound to IntelAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import IntelAuditRecord


def make_intelligence_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained intelligence audit log."""
    return ImmutableAuditLog(record_cls=IntelAuditRecord)


__all__ = ["make_intelligence_audit_log", "ImmutableAuditLog", "AuditError"]
