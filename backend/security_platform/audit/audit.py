"""Security audit log = the shared ImmutableAuditLog bound to SecurityAuditRecord (DRP5-H).

No parallel audit system: the Security Platform reuses the platform's single hash-chained
:class:`ImmutableAuditLog` (V2-P1), parameterised with the :class:`SecurityAuditRecord`. Every
authentication / authorization / policy / access / credential / validation event is appended
immutably and is tamper-evident (append-only, immutable, traceable).
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import SecurityAuditRecord


def make_security_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained security audit log."""
    return ImmutableAuditLog(record_cls=SecurityAuditRecord)


__all__ = ["make_security_audit_log", "ImmutableAuditLog", "AuditError"]
