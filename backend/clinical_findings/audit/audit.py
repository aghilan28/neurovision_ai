"""Finding audit log = the shared ImmutableAuditLog bound to FindingAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import FindingAuditRecord


def make_finding_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained finding audit log."""
    return ImmutableAuditLog(record_cls=FindingAuditRecord)


__all__ = ["make_finding_audit_log", "ImmutableAuditLog", "AuditError"]
