"""Event audit log = the shared ImmutableAuditLog bound to EventAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import EventAuditRecord


def make_event_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained operational-event audit log."""
    return ImmutableAuditLog(record_cls=EventAuditRecord)


__all__ = ["make_event_audit_log", "ImmutableAuditLog", "AuditError"]
