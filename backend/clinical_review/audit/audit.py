"""Review audit log = the shared ImmutableAuditLog bound to ReviewAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import ReviewAuditRecord


def make_review_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained review audit log."""
    return ImmutableAuditLog(record_cls=ReviewAuditRecord)


__all__ = ["make_review_audit_log", "ImmutableAuditLog", "AuditError"]
