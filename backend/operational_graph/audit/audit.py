"""Graph audit log = the shared ImmutableAuditLog bound to GraphAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..nodes.domain import GraphAuditRecord


def make_graph_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained operational-graph audit log."""
    return ImmutableAuditLog(record_cls=GraphAuditRecord)


__all__ = ["make_graph_audit_log", "ImmutableAuditLog", "AuditError"]
