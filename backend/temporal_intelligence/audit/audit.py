"""Temporal audit log = the shared ImmutableAuditLog bound to TemporalAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import TemporalAuditRecord


def make_temporal_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained temporal-intelligence audit log."""
    return ImmutableAuditLog(record_cls=TemporalAuditRecord)


__all__ = ["make_temporal_audit_log", "ImmutableAuditLog", "AuditError"]
