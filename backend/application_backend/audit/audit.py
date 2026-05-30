"""Application audit log = the shared ImmutableAuditLog bound to ``BackendAuditRecord``.

No parallel audit system: the Application Backend reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with
:class:`BackendAuditRecord`. Every registration / authentication / session / upload /
workflow / request / response event is appended immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import BackendAuditRecord


def make_backend_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained application audit log."""
    return ImmutableAuditLog(record_cls=BackendAuditRecord)


__all__ = ["make_backend_audit_log", "ImmutableAuditLog", "AuditError"]
