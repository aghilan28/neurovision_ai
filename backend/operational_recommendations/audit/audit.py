"""Recommendation audit log = the shared ImmutableAuditLog bound to the record.

No parallel audit system: the recommendation layer reuses the platform's single
hash-chained :class:`ImmutableAuditLog` implementation (V2-P1), parameterised with
:class:`RecommendationAuditRecord`. Every guidance/priority/optimization/escalation
generation, version change, registration and validation event is appended immutably
here.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import RecommendationAuditRecord


def make_recommendation_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained operational-recommendation audit log."""
    return ImmutableAuditLog(record_cls=RecommendationAuditRecord)


__all__ = ["make_recommendation_audit_log", "ImmutableAuditLog", "AuditError"]
