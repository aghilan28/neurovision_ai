"""EEG audit log = the shared ImmutableAuditLog bound to ``EEGAuditRecord``.

No parallel audit system: the EEG foundation reuses the platform's single
hash-chained :class:`ImmutableAuditLog` (V2-P1), parameterised with
:class:`EEGAuditRecord`. Every ingestion, validation, metadata-extraction,
storage, lineage, version, and registration event is appended immutably and is
tamper-evident.
"""

from __future__ import annotations

from backend.clinical_cases.audit import ImmutableAuditLog, AuditError  # intra-backend reuse

from ..models.domain import EEGAuditRecord


def make_eeg_audit_log() -> ImmutableAuditLog:
    """Return an empty, hash-chained EEG audit log."""
    return ImmutableAuditLog(record_cls=EEGAuditRecord)


__all__ = ["make_eeg_audit_log", "ImmutableAuditLog", "AuditError"]
