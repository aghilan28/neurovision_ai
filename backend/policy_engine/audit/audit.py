"""Policy audit log = the shared ImmutableAuditLog bound to PolicyAuditRecord.

No parallel audit system: the policy engine reuses the platform's single
hash-chained :class:`ImmutableAuditLog` implementation (V2-P1), parameterised with
:class:`PolicyAuditRecord`. Every policy creation/update, constraint change,
evaluation event, approval/suspension event, and version change is appended here.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import PolicyAuditRecord


def make_policy_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained policy audit log."""
    return ImmutableAuditLog(record_cls=PolicyAuditRecord)


__all__ = ["make_policy_audit_log", "ImmutableAuditLog", "AuditError"]
