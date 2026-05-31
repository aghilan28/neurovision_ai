"""Validation audit log = the shared ImmutableAuditLog bound to ValidationAuditRecord (DRP6-H).

No parallel audit system: the Clinical Validation Platform reuses the platform's single
hash-chained :class:`ImmutableAuditLog`, parameterised with the :class:`ValidationAuditRecord`.
Every benchmark / calibration / reliability / comparison / evidence / readiness event is
appended immutably and is tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import ValidationAuditRecord


def make_validation_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained clinical-validation audit log."""
    return ImmutableAuditLog(record_cls=ValidationAuditRecord)


__all__ = ["make_validation_audit_log", "ImmutableAuditLog", "AuditError"]
