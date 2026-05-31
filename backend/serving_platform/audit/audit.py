"""Serving audit log = the shared ImmutableAuditLog bound to ServingAuditRecord.

No parallel audit system: the Serving Platform reuses the platform's single hash-chained
:class:`ImmutableAuditLog` (V2-P1), parameterised with the serving
:class:`ServingAuditRecord`. Every request / validation / model-selection / execution /
response / lifecycle / readiness / lineage / version / registration event is appended
immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import ServingAuditRecord


def make_serving_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained serving audit log."""
    return ImmutableAuditLog(record_cls=ServingAuditRecord)


__all__ = ["make_serving_audit_log", "ImmutableAuditLog", "AuditError"]
