"""Goal audit log = the shared ImmutableAuditLog bound to GoalAuditRecord.

No parallel audit system: the goal subsystem reuses the platform's single
hash-chained :class:`ImmutableAuditLog` implementation (V2-P1), parameterised with
:class:`GoalAuditRecord`. Every creation/modification/approval/activation/
suspension/completion/archival, relationship change, and version change is appended
immutably here.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import GoalAuditRecord


def make_goal_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained goal audit log."""
    return ImmutableAuditLog(record_cls=GoalAuditRecord)


__all__ = ["make_goal_audit_log", "ImmutableAuditLog", "AuditError"]
