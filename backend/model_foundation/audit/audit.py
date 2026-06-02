"""Model audit log = the shared ImmutableAuditLog bound to ``ModelAuditRecord``.

No parallel audit system: the Model Foundation layer reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with
:class:`ModelAuditRecord`. Every dataset / training / evaluation / experiment /
model / lineage / version / registration event is appended immutably and is
tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import ModelAuditRecord


def make_model_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained model audit log."""
    return ImmutableAuditLog(record_cls=ModelAuditRecord)


__all__ = ["make_model_audit_log", "ImmutableAuditLog", "AuditError"]
