"""Decision audit log = the shared ImmutableAuditLog bound to DecisionAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import DecisionAuditRecord


def make_decision_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained decision-support audit log."""
    return ImmutableAuditLog(record_cls=DecisionAuditRecord)


__all__ = ["make_decision_audit_log", "ImmutableAuditLog", "AuditError"]
