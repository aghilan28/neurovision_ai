"""Production-model audit log = the shared ImmutableAuditLog bound to ModelAuditRecord.

No parallel audit system: the Production Model layer reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with the production
:class:`ModelAuditRecord`. Every dataset / training / experiment / evaluation / model /
benchmark / readiness / lineage / version / registration event is appended immutably and
is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import ModelAuditRecord


def make_production_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained production-model audit log."""
    return ImmutableAuditLog(record_cls=ModelAuditRecord)


__all__ = ["make_production_audit_log", "ImmutableAuditLog", "AuditError"]
