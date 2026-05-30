"""Agent audit log = the shared ImmutableAuditLog bound to AgentAuditRecord.

No parallel audit system: the agent subsystem reuses the platform's single
hash-chained :class:`ImmutableAuditLog` implementation (V2-P1), parameterised with
:class:`AgentAuditRecord`. Every creation/modification/approval/availability/
suspension/retirement, assignment change, capability change, and version change is
appended immutably.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import AgentAuditRecord


def make_agent_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained agent audit log."""
    return ImmutableAuditLog(record_cls=AgentAuditRecord)


__all__ = ["make_agent_audit_log", "ImmutableAuditLog", "AuditError"]
