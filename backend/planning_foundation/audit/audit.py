"""Plan audit log = the shared ImmutableAuditLog bound to PlanAuditRecord.

No parallel audit system: the planning subsystem reuses the platform's single
hash-chained :class:`ImmutableAuditLog` implementation (V2-P1), parameterised with
:class:`PlanAuditRecord`. Every creation/modification/approval/readiness/suspension/
completion/archival, dependency change, and version change is appended immutably.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import PlanAuditRecord


def make_plan_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained plan audit log."""
    return ImmutableAuditLog(record_cls=PlanAuditRecord)


__all__ = ["make_plan_audit_log", "ImmutableAuditLog", "AuditError"]
