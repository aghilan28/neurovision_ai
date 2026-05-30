"""Analytics audit log = the shared ImmutableAuditLog bound to AnalyticsAuditRecord.

No parallel audit system: the analytics layer reuses the platform's single
hash-chained :class:`ImmutableAuditLog` implementation (V2-P1), parameterised with
:class:`AnalyticsAuditRecord`. Every metric/health/trend/risk generation, version
change, registration and validation event is appended immutably here.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import AnalyticsAuditRecord


def make_analytics_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained operational-analytics audit log."""
    return ImmutableAuditLog(record_cls=AnalyticsAuditRecord)


__all__ = ["make_analytics_audit_log", "ImmutableAuditLog", "AuditError"]
