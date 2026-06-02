"""Governance-intelligence audit log = the shared ImmutableAuditLog bound to
``GovernanceAuditRecord``.

No parallel audit system: the governance-intelligence subsystem reuses the
platform's single hash-chained :class:`ImmutableAuditLog` implementation (V2-P1),
parameterised with :class:`GovernanceAuditRecord`. Every intelligence generation,
violation detection, escalation analysis, risk analysis, validation event, and
version change is appended immutably.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import GovernanceAuditRecord


def make_governance_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained governance-intelligence audit log."""
    return ImmutableAuditLog(record_cls=GovernanceAuditRecord)


__all__ = ["make_governance_audit_log", "ImmutableAuditLog", "AuditError"]
