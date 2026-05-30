"""Feature audit log = the shared ImmutableAuditLog bound to ``FeatureAuditRecord``.

No parallel audit system: the Feature Engineering layer reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with
:class:`FeatureAuditRecord`. Every extraction / validation / lineage / version /
registration event is appended immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import FeatureAuditRecord


def make_feature_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained feature audit log."""
    return ImmutableAuditLog(record_cls=FeatureAuditRecord)


__all__ = ["make_feature_audit_log", "ImmutableAuditLog", "AuditError"]
