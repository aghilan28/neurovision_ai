"""Persistence audit log = the shared ImmutableAuditLog bound to PersistenceAuditRecord.

No parallel audit system (DRP4-L): the Persistence Platform reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with the persistence
:class:`PersistenceAuditRecord`. Every storage / repository / registry / audit / lineage /
execution / persist / recover / validate / version event is appended immutably and is
tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import PersistenceAuditRecord


def make_persistence_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained persistence audit log."""
    return ImmutableAuditLog(record_cls=PersistenceAuditRecord)


__all__ = ["make_persistence_audit_log", "ImmutableAuditLog", "AuditError"]
