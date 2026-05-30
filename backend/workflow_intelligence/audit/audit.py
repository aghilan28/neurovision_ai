"""Workflow audit log = the shared ImmutableAuditLog bound to WorkflowAuditRecord."""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import WorkflowAuditRecord


def make_workflow_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained workflow-intelligence audit log."""
    return ImmutableAuditLog(record_cls=WorkflowAuditRecord)


__all__ = ["make_workflow_audit_log", "ImmutableAuditLog", "AuditError"]
