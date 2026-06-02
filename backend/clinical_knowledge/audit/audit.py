"""Knowledge audit log = the shared ImmutableAuditLog bound to KnowledgeAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import KnowledgeAuditRecord


def make_knowledge_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained knowledge audit log."""
    return ImmutableAuditLog(record_cls=KnowledgeAuditRecord)


__all__ = ["make_knowledge_audit_log", "ImmutableAuditLog", "AuditError"]
